param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('namespace', 'ghcr-secret', 'gcp-sa-secret', 'helm-install', 'helm-migrate', 'helm-install-worker', 'helm-install-loki', 'helm-install-promtail', 'helm-install-grafana', 'helm-install-metrics', 'helm-install-logging', 'helm-install-observability', 'deploy', 'deploy-all', 'undeploy', 'undeploy-keep-pg', 'undeploy-apps', 'pg-port-forward', 'grafana-port-forward', 'docker-login-ghcr', 'docker-build', 'docker-build-push-worker', 'rollout-worker', 'update-worker-image', 'limit-workers')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '../..')
$EnvFile = Join-Path $ProjectRoot '.env'
$ChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/postgres'
$MigrateChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/db-migrate'
$WorkerChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/task-worker'
$PromtailChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/promtail'
$LokiChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/loki'
$GrafanaChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/grafana'
$MetricsChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/metrics'
$MigrationsSrc = Join-Path $ProjectRoot 'deployment/db/migrations'

function Load-DotEnv {
    param([string]$Path)
    # Optional .env: fill missing process env keys only; never overwrite existing values.
    if (-not (Test-Path $Path)) {
        Write-Host ('[INFO] .env not found at ' + $Path + '; skip')
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line -match '^([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            $existing = [Environment]::GetEnvironmentVariable($name, 'Process')
            if (-not [string]::IsNullOrWhiteSpace($existing)) {
                return
            }
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

function Require-EnvVar {
    param([string]$Name)
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "$Name not set in .env"
    }
}

Load-DotEnv -Path $EnvFile

$GhcrSecretName = if ($env:GHCR_SECRET_NAME) { $env:GHCR_SECRET_NAME } else { 'ghcr-secret' }
$GcpSaSecretName = if ($env:GCP_SA_SECRET_NAME) { $env:GCP_SA_SECRET_NAME } else { 'gcp-sa-key' }
$GcpSaKeyPath = if ($env:GCP_SA_KEY_FILE) { $env:GCP_SA_KEY_FILE } else { 'deployment/secrets/gcp-sa.json' }
$DockerImage = if ($env:DOCKER_IMAGE) { $env:DOCKER_IMAGE } else { 'ghcr.io/royceazure/stock-ana-atsk-worker' }
$Dockerfile = Join-Path $ProjectRoot 'deployment/docker/Dockerfile'

function Write-Info {
    param([string]$Message)
    Write-Host ('[INFO] ' + $Message)
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @()
    )
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw ("Command failed (exit $LASTEXITCODE): $FilePath " + ($ArgumentList -join ' '))
    }
}

function Get-DockerImageRef {
    $appEnv = Get-AppEnv
    $tag = if ($env:DOCKER_TAG) { $env:DOCKER_TAG } else { "${appEnv}-latest" }
    return "${DockerImage}:${tag}"
}

function Invoke-DockerLoginGhcr {
    Require-EnvVar 'GITHUB_USER'
    Require-EnvVar 'GITHUB_PAT'
    Write-Info ("docker login ghcr.io as $($env:GITHUB_USER)")
    $env:GITHUB_PAT | docker login ghcr.io -u $env:GITHUB_USER --password-stdin
    if ($LASTEXITCODE -ne 0) {
        throw "docker login ghcr.io failed (exit $LASTEXITCODE)"
    }
}

function Invoke-DockerBuild {
    $imageRef = Get-DockerImageRef
    Write-Info ("docker build -t $imageRef")
    Push-Location $ProjectRoot
    try {
        Invoke-External -FilePath docker -ArgumentList @('build', '-f', $Dockerfile, '-t', $imageRef, '.')
    }
    finally {
        Pop-Location
    }
}

function Invoke-DockerBuildPushWorker {
    Invoke-DockerLoginGhcr
    Invoke-DockerBuild
    $imageRef = Get-DockerImageRef
    Write-Info ("docker push $imageRef")
    Invoke-External -FilePath docker -ArgumentList @('push', $imageRef)
}

function Add-HelmSetFromEnv {
    param(
        [System.Collections.Generic.List[string]]$Target,
        [string]$EnvName,
        [string]$HelmKey
    )
    $value = [Environment]::GetEnvironmentVariable($EnvName, 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) {
        return
    }
    $Target.Add('--set')
    $Target.Add("${HelmKey}=$value")
    Write-Info ('Helm ' + $HelmKey + ' from .env (' + $EnvName + ')')
}


function Get-AppEnv {
    $value = [Environment]::GetEnvironmentVariable('APP_ENV', 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = 'dev'
    }
    $value = $value.Trim().ToLowerInvariant()
    if ($value -notin @('dev', 'prod')) {
        throw 'APP_ENV must be dev or prod'
    }
    return $value
}

function Get-PostgresHelmSetArgs {
    $sets = [System.Collections.Generic.List[string]]::new()
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_DATABASE' -HelmKey 'postgresql.database'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_USER' -HelmKey 'postgresql.username'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_PASSWORD' -HelmKey 'postgresql.password'
    return $sets
}

function Get-MigrateHelmSetArgs {
    $sets = [System.Collections.Generic.List[string]]::new()
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_DATABASE' -HelmKey 'postgres.database'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_USER' -HelmKey 'postgres.username'
    return $sets
}

function Get-WorkerHelmSetArgs {
    $sets = [System.Collections.Generic.List[string]]::new()
    $appEnv = Get-AppEnv
    $sets.Add('--set')
    $sets.Add("image.tag=${appEnv}-latest")
    Write-Info ("Helm image.tag from APP_ENV (${appEnv}-latest)")
    $sets.Add('--set')
    $sets.Add("worker.appEnv=$appEnv")
    Write-Info ("Helm worker.appEnv from APP_ENV ($appEnv)")
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_DATABASE' -HelmKey 'postgres.database'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_USER' -HelmKey 'postgres.username'
    Add-HelmSetFromEnv -Target $sets -EnvName 'WORKER_TASK_TYPES' -HelmKey 'worker.taskTypes'
    Add-HelmSetFromEnv -Target $sets -EnvName 'LOG_LEVEL' -HelmKey 'worker.logLevel'
    Add-HelmSetFromEnv -Target $sets -EnvName 'GCP_PROJECT_ID' -HelmKey 'gcp.projectId'
    Add-HelmSetFromEnv -Target $sets -EnvName 'GCP_TASK_SUBSCRIPTION_ID' -HelmKey 'gcp.taskSubscriptionId'
    Add-HelmSetFromEnv -Target $sets -EnvName 'GCP_AUTH_MODE' -HelmKey 'gcp.authMode'
    Add-HelmSetFromEnv -Target $sets -EnvName 'OBJECT_STORAGE_BUCKET_BASE_PATH' -HelmKey 'gcp.objectStorageBucketBasePath'
    Add-HelmSetFromEnv -Target $sets -EnvName 'DUCKDB_POOL_SIZE' -HelmKey 'worker.duckdbPoolSize'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_POOL_MIN_CONN' -HelmKey 'worker.pgPoolMinConn'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PG_POOL_MAX_CONN' -HelmKey 'worker.pgPoolMaxConn'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PUBSUB_BATCH_SIZE' -HelmKey 'worker.pubsubBatchSize'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PUBSUB_VISIBILITY_TIMEOUT' -HelmKey 'worker.pubsubVisibilityTimeout'
    Add-HelmSetFromEnv -Target $sets -EnvName 'PUBSUB_PULL_TIMEOUT' -HelmKey 'worker.pubsubPullTimeout'
    Add-HelmSetFromEnv -Target $sets -EnvName 'SHUTDOWN_DRAIN_TIMEOUT' -HelmKey 'worker.shutdownDrainTimeout'
    return $sets
}

function Get-PromtailHelmSetArgs {
    $sets = [System.Collections.Generic.List[string]]::new()
    Add-HelmSetFromEnv -Target $sets -EnvName 'K8S_NAMESPACE' -HelmKey 'scrapeNamespaces[0]'
    Add-HelmSetFromEnv -Target $sets -EnvName 'LOKI_PUSH_URL' -HelmKey 'loki.url'
    return $sets
}

function Get-GrafanaHelmSetArgs {
    $sets = [System.Collections.Generic.List[string]]::new()
    Add-HelmSetFromEnv -Target $sets -EnvName 'GRAFANA_ADMIN_PASSWORD' -HelmKey 'admin.password'
    $releaseName = [Environment]::GetEnvironmentVariable('K8S_RELEASE_NAME', 'Process')
    if (-not [string]::IsNullOrWhiteSpace($releaseName)) {
        $sets.Add('--set')
        $sets.Add("dashboards.worker.podRegex=$releaseName-worker.*")
        Write-Info ('Helm dashboards.worker.podRegex from .env (K8S_RELEASE_NAME): ' + $releaseName + '-worker.*')
    }
    $promDatasource = [Environment]::GetEnvironmentVariable('GRAFANA_PROMETHEUS_DATASOURCE_ENABLED', 'Process')
    if ($promDatasource -and @('0', 'false', 'no') -contains $promDatasource.Trim().ToLower()) {
        $sets.Add('--set')
        $sets.Add('prometheus.enabled=false')
        $sets.Add('--set')
        $sets.Add('dashboards.enabled=false')
        Write-Info 'Helm prometheus.enabled=false from .env (GRAFANA_PROMETHEUS_DATASOURCE_ENABLED)'
    }
    return $sets
}

function Get-MetricsHelmSetArgs {
    $sets = [System.Collections.Generic.List[string]]::new()
    Add-HelmSetFromEnv -Target $sets -EnvName 'K8S_NAMESPACE' -HelmKey 'scrapeNamespaces[0]'
    $spotTolerations = [Environment]::GetEnvironmentVariable('METRICS_NODE_EXPORTER_SPOT_TOLERATIONS', 'Process')
    if ($spotTolerations -and @('1', 'true', 'yes') -contains $spotTolerations.Trim().ToLower()) {
        $sets.Add('--set')
        $sets.Add('nodeExporter.spotTolerations.enabled=true')
        Write-Info 'Helm nodeExporter.spotTolerations.enabled=true from .env (METRICS_NODE_EXPORTER_SPOT_TOLERATIONS)'
    }
    return $sets
}

function Ensure-Namespace {
    Require-EnvVar 'K8S_NAMESPACE'
    kubectl create namespace $env:K8S_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
}

function Ensure-GhcrSecret {
    Require-EnvVar 'GITHUB_USER'
    Require-EnvVar 'GITHUB_PAT'
    Require-EnvVar 'K8S_NAMESPACE'
    kubectl create secret docker-registry $GhcrSecretName `
        --docker-server=ghcr.io `
        --docker-username=$env:GITHUB_USER `
        --docker-password=$env:GITHUB_PAT `
        --namespace=$env:K8S_NAMESPACE `
        --dry-run=client -o yaml | kubectl apply -f -
}

function Ensure-GcpSaSecret {
    Require-EnvVar 'K8S_NAMESPACE'
    $authMode = if ($env:GCP_AUTH_MODE) { $env:GCP_AUTH_MODE.Trim().ToLower() } else { 'adc' }
    if ($authMode -ne 'service_account_json') {
        Write-Info ('GCP_AUTH_MODE=' + $authMode + '; skipping gcp-sa-key Secret')
        return
    }
    $keyFile = Join-Path $ProjectRoot $GcpSaKeyPath
    if (-not (Test-Path $keyFile)) {
        throw ('GCP SA key not found at ' + $keyFile + '; use deployment/secrets/gcp-sa.json or set GCP_SA_KEY_FILE')
    }
    kubectl create secret generic $GcpSaSecretName `
        --from-file=key.json=$keyFile `
        --namespace=$env:K8S_NAMESPACE `
        --dry-run=client -o yaml | kubectl apply -f -
    Write-Info ('GCP SA secret ' + $GcpSaSecretName + ' applied')
}

function Install-Postgres {
    Require-EnvVar 'K8S_RELEASE_NAME'
    Require-EnvVar 'K8S_NAMESPACE'
    $helmArgs = [System.Collections.Generic.List[string]]::new()
    $helmArgs.Add('upgrade')
    $helmArgs.Add('--install')
    $helmArgs.Add($env:K8S_RELEASE_NAME)
    $helmArgs.Add($ChartPath)
    $helmArgs.Add('--namespace')
    $helmArgs.Add($env:K8S_NAMESPACE)
    $helmArgs.Add('--set')
    $helmArgs.Add("imagePullSecretName=$GhcrSecretName")
    foreach ($arg in (Get-PostgresHelmSetArgs)) {
        $helmArgs.Add($arg)
    }
    & helm @helmArgs
}

function Get-MigrateReleaseName {
    Require-EnvVar 'K8S_RELEASE_NAME'
    return "$($env:K8S_RELEASE_NAME)-migrate"
}

function Get-WorkerReleaseName {
    Require-EnvVar 'K8S_RELEASE_NAME'
    return "$($env:K8S_RELEASE_NAME)-worker"
}

function Get-PromtailReleaseName {
    Require-EnvVar 'K8S_RELEASE_NAME'
    return "$($env:K8S_RELEASE_NAME)-promtail"
}

function Get-LokiReleaseName {
    Require-EnvVar 'K8S_RELEASE_NAME'
    return "$($env:K8S_RELEASE_NAME)-loki"
}

function Get-GrafanaReleaseName {
    Require-EnvVar 'K8S_RELEASE_NAME'
    return "$($env:K8S_RELEASE_NAME)-grafana"
}

function Get-MetricsReleaseName {
    Require-EnvVar 'K8S_RELEASE_NAME'
    return "$($env:K8S_RELEASE_NAME)-metrics"
}

function Sync-MigrationFiles {
    $migrationsDst = Join-Path $MigrateChartPath 'migrations'
    if (-not (Test-Path $MigrationsSrc)) {
        throw "Migrations not found at $MigrationsSrc"
    }
    if (Test-Path $migrationsDst) {
        Remove-Item $migrationsDst -Recurse -Force
    }
    Copy-Item -Recurse $MigrationsSrc $migrationsDst
}

function Wait-ForPostgres {
    Require-EnvVar 'K8S_NAMESPACE'
    Write-Host "Waiting for postgres pod ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n $env:K8S_NAMESPACE --timeout=180s
}

function Install-DbMigrate {
    Require-EnvVar 'K8S_RELEASE_NAME'
    Require-EnvVar 'K8S_NAMESPACE'
    Sync-MigrationFiles
    $migrateRelease = Get-MigrateReleaseName
    $helmArgs = [System.Collections.Generic.List[string]]::new()
    $helmArgs.Add('upgrade')
    $helmArgs.Add('--install')
    $helmArgs.Add($migrateRelease)
    $helmArgs.Add($MigrateChartPath)
    $helmArgs.Add('--namespace')
    $helmArgs.Add($env:K8S_NAMESPACE)
    $helmArgs.Add('--set')
    $helmArgs.Add("postgres.releaseName=$($env:K8S_RELEASE_NAME)")
    $helmArgs.Add('--set')
    $helmArgs.Add("imagePullSecretName=$GhcrSecretName")
    foreach ($arg in (Get-MigrateHelmSetArgs)) {
        $helmArgs.Add($arg)
    }
    $helmArgs.Add('--wait')
    $helmArgs.Add('--timeout')
    $helmArgs.Add('5m')
    & helm @helmArgs
    Write-Host "Migration job completed (golang-migrate up is idempotent)."
}

function Install-TaskWorker {
    Require-EnvVar 'K8S_RELEASE_NAME'
    Require-EnvVar 'K8S_NAMESPACE'
    Require-EnvVar 'GCP_PROJECT_ID'
    Require-EnvVar 'GCP_TASK_SUBSCRIPTION_ID'
    Require-EnvVar 'OBJECT_STORAGE_BUCKET_BASE_PATH'

    $workerRelease = Get-WorkerReleaseName
    $helmArgs = [System.Collections.Generic.List[string]]::new()
    $helmArgs.Add('upgrade')
    $helmArgs.Add('--install')
    $helmArgs.Add($workerRelease)
    $helmArgs.Add($WorkerChartPath)
    $helmArgs.Add('--namespace')
    $helmArgs.Add($env:K8S_NAMESPACE)
    $helmArgs.Add('--set')
    $helmArgs.Add("imagePullSecretName=$GhcrSecretName")
    $helmArgs.Add('--set')
    $helmArgs.Add("postgres.releaseName=$($env:K8S_RELEASE_NAME)")
    $helmArgs.Add('--set')
    $helmArgs.Add("fullnameOverride=$workerRelease")
    $helmArgs.Add('--set')
    $helmArgs.Add("gcp.serviceAccount.existingSecretName=$GcpSaSecretName")
    foreach ($arg in (Get-WorkerHelmSetArgs)) {
        $helmArgs.Add($arg)
    }
    & helm @helmArgs
    Write-Host "Task worker deployed: $workerRelease"
}

function Restart-TaskWorker {
    Require-EnvVar 'K8S_NAMESPACE'
    $workerRelease = Get-WorkerReleaseName
    $imageRef = "$(Get-DockerImageRef)"
    Write-Info "Rollout restart deployment/$workerRelease in $($env:K8S_NAMESPACE) (image: $imageRef)"
    kubectl rollout restart "deployment/$workerRelease" -n $env:K8S_NAMESPACE
    kubectl rollout status "deployment/$workerRelease" -n $env:K8S_NAMESPACE --timeout=5m
    Write-Host "Worker rollout complete: $workerRelease"
}

function Update-TaskWorkerImage {
    Invoke-DockerBuildPushWorker
    Restart-TaskWorker
}

function Limit-KindWorkers {
    <#
    模擬 GKE 兩類 node pool：
      - resident：常駐觀測/DB 節點，Docker mem=2g，label node-type=resident
      - scale：水平擴展 worker 節點，Docker mem=1g，label node-type=scale
    kind worker 依名稱排序：第一台=resident、第二台=scale。
    #>
    $workers = @(docker ps --filter 'label=io.x-k8s.kind.role=worker' --format '{{.Names}}' |
        Where-Object { $_ } |
        Sort-Object)
    if ($workers.Count -lt 2) {
        throw "Expected at least 2 kind worker containers, found $($workers.Count): $($workers -join ', ')"
    }

    $resident = $workers[0]
    $scale = $workers[1]

    Write-Info "Resident node: $resident -> cpus=2.0 memory=2g label node-type=resident"
    Invoke-External -FilePath 'docker' -ArgumentList @(
        'update', '--cpus=2.0', '--memory=2g', '--memory-swap=2g', $resident
    )
    Invoke-External -FilePath 'kubectl' -ArgumentList @(
        'label', 'node', $resident, 'node-type=resident', '--overwrite'
    )

    Write-Info "Scale node: $scale -> cpus=2.0 memory=1g label node-type=scale"
    Invoke-External -FilePath 'docker' -ArgumentList @(
        'update', '--cpus=2.0', '--memory=1g', '--memory-swap=1g', $scale
    )
    Invoke-External -FilePath 'kubectl' -ArgumentList @(
        'label', 'node', $scale, 'node-type=scale', '--overwrite'
    )

    if ($workers.Count -gt 2) {
        Write-Info "Extra workers ignored (only first two used): $($workers[2..($workers.Count - 1)] -join ', ')"
    }

    Write-Host ''
    Write-Host 'Node pool mapping (for nodeSelector tests):'
    Write-Host "  $resident  node-type=resident  (2g mem)  <- observability / DB"
    Write-Host "  $scale     node-type=scale     (1g mem)  <- task-worker / spot"
    Write-Host ''
    Write-Host 'Verify:'
    Write-Host '  kubectl get nodes -L node-type'
    Write-Host '  docker stats --no-stream $(docker ps --filter label=io.x-k8s.kind.role=worker -q)'
}

function Install-Promtail {
    Require-EnvVar 'K8S_NAMESPACE'
    $promtailRelease = Get-PromtailReleaseName
    $helmArgs = [System.Collections.Generic.List[string]]::new()
    $helmArgs.Add('upgrade')
    $helmArgs.Add('--install')
    $helmArgs.Add($promtailRelease)
    $helmArgs.Add($PromtailChartPath)
    $helmArgs.Add('--namespace')
    $helmArgs.Add($env:K8S_NAMESPACE)
    $helmArgs.Add('--set')
    $helmArgs.Add("imagePullSecretName=$GhcrSecretName")
    $helmArgs.Add('--set')
    $helmArgs.Add("fullnameOverride=$promtailRelease")
    foreach ($arg in (Get-PromtailHelmSetArgs)) {
        $helmArgs.Add($arg)
    }
    & helm @helmArgs
    Write-Host "Promtail deployed: $promtailRelease (DaemonSet)"
}

function Install-Loki {
    Require-EnvVar 'K8S_NAMESPACE'
    $lokiRelease = Get-LokiReleaseName
    $helmArgs = [System.Collections.Generic.List[string]]::new()
    $helmArgs.Add('upgrade')
    $helmArgs.Add('--install')
    $helmArgs.Add($lokiRelease)
    $helmArgs.Add($LokiChartPath)
    $helmArgs.Add('--namespace')
    $helmArgs.Add($env:K8S_NAMESPACE)
    $helmArgs.Add('--set')
    $helmArgs.Add("imagePullSecretName=$GhcrSecretName")
    $helmArgs.Add('--set')
    $helmArgs.Add('fullnameOverride=loki')
    $helmArgs.Add('--wait')
    $helmArgs.Add('--timeout')
    $helmArgs.Add('5m')
    & helm @helmArgs
    Write-Host ('Loki deployed: ' + $lokiRelease + ' (Service: loki.' + $env:K8S_NAMESPACE + '.svc.cluster.local:3100)')
}

function Wait-ForLoki {
    Require-EnvVar 'K8S_NAMESPACE'
    Write-Host "Waiting for loki pod ready..."
    kubectl wait --for=condition=ready pod -l app=loki -n $env:K8S_NAMESPACE --timeout=180s
}

function Install-Metrics {
    Require-EnvVar 'K8S_NAMESPACE'
    $metricsRelease = Get-MetricsReleaseName
    $helmArgs = [System.Collections.Generic.List[string]]::new()
    $helmArgs.Add('upgrade')
    $helmArgs.Add('--install')
    $helmArgs.Add($metricsRelease)
    $helmArgs.Add($MetricsChartPath)
    $helmArgs.Add('--namespace')
    $helmArgs.Add($env:K8S_NAMESPACE)
    $helmArgs.Add('--set')
    $helmArgs.Add("imagePullSecretName=$GhcrSecretName")
    $helmArgs.Add('--set')
    $helmArgs.Add('prometheus.fullnameOverride=prometheus')
    $helmArgs.Add('--set')
    $helmArgs.Add('nodeExporter.fullnameOverride=node-exporter')
    $helmArgs.Add('--set')
    $helmArgs.Add('kubeStateMetrics.fullnameOverride=kube-state-metrics')
    foreach ($arg in (Get-MetricsHelmSetArgs)) {
        $helmArgs.Add($arg)
    }
    $helmArgs.Add('--wait')
    $helmArgs.Add('--timeout')
    $helmArgs.Add('5m')
    & helm @helmArgs
    Write-Host ('Metrics deployed: ' + $metricsRelease + ' (Prometheus + node-exporter + kube-state-metrics)')
    Write-Host ('Prometheus: http://prometheus.' + $env:K8S_NAMESPACE + '.svc.cluster.local:9090')
}

function Wait-ForMetrics {
    Require-EnvVar 'K8S_NAMESPACE'
    Write-Host "Waiting for prometheus pod ready..."
    kubectl wait --for=condition=ready pod -l app=prometheus -n $env:K8S_NAMESPACE --timeout=180s
}

function Install-Grafana {
    Require-EnvVar 'K8S_NAMESPACE'
    $grafanaRelease = Get-GrafanaReleaseName
    $helmArgs = [System.Collections.Generic.List[string]]::new()
    $helmArgs.Add('upgrade')
    $helmArgs.Add('--install')
    $helmArgs.Add($grafanaRelease)
    $helmArgs.Add($GrafanaChartPath)
    $helmArgs.Add('--namespace')
    $helmArgs.Add($env:K8S_NAMESPACE)
    $helmArgs.Add('--set')
    $helmArgs.Add("imagePullSecretName=$GhcrSecretName")
    $helmArgs.Add('--set')
    $helmArgs.Add('fullnameOverride=grafana')
    foreach ($arg in (Get-GrafanaHelmSetArgs)) {
        $helmArgs.Add($arg)
    }
    $helmArgs.Add('--wait')
    $helmArgs.Add('--timeout')
    $helmArgs.Add('5m')
    & helm @helmArgs
    Write-Host ('Grafana deployed: ' + $grafanaRelease + ' (Service: grafana.' + $env:K8S_NAMESPACE + '.svc.cluster.local:3000)')
}

function Start-GrafanaPortForward {
    Require-EnvVar 'K8S_NAMESPACE'
    $localPort = if ($env:GRAFANA_LOCAL_PORT) { $env:GRAFANA_LOCAL_PORT } else { '3000' }
    Write-Host "Forwarding localhost:$localPort -> grafana.$($env:K8S_NAMESPACE):3000 (Ctrl+C to stop)"
    Write-Host "Login: admin / (see .env GRAFANA_ADMIN_PASSWORD or chart default)"
    kubectl port-forward -n $env:K8S_NAMESPACE svc/grafana "${localPort}:3000"
}

function Start-PgPortForward {
    Require-EnvVar 'K8S_RELEASE_NAME'
    Require-EnvVar 'K8S_NAMESPACE'
    $localPort = if ($env:PG_LOCAL_PORT) { $env:PG_LOCAL_PORT } else { '5432' }
    $svc = "$($env:K8S_RELEASE_NAME)-postgres"
    $target = "$svc.$($env:K8S_NAMESPACE):5432"
    Write-Host "Forwarding localhost:$localPort -> $target (Ctrl+C to stop)"
    kubectl port-forward -n $env:K8S_NAMESPACE "svc/$svc" "${localPort}:5432"
}

function Invoke-HelmUninstallIfExists {
    param(
        [string]$Release,
        [string]$Namespace
    )
    $prevErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = helm uninstall $Release --namespace $Namespace 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info ('Uninstalled Helm release: ' + $Release)
            return
        }
        if ($output -match 'release: not found') {
            Write-Info ('Helm release not found, skipped: ' + $Release)
            return
        }
        throw ($output | Out-String)
    } finally {
        $ErrorActionPreference = $prevErrorAction
    }
}

function Uninstall-WorkerAndMigrate {
    Require-EnvVar 'K8S_NAMESPACE'
    $migrateRelease = Get-MigrateReleaseName
    $workerRelease = Get-WorkerReleaseName
    Invoke-HelmUninstallIfExists -Release $workerRelease -Namespace $env:K8S_NAMESPACE
    Invoke-HelmUninstallIfExists -Release $migrateRelease -Namespace $env:K8S_NAMESPACE
}

function Uninstall-AllKeepPgVolume {
    Require-EnvVar 'K8S_RELEASE_NAME'
    Require-EnvVar 'K8S_NAMESPACE'
    Uninstall-WorkerAndMigrate
    Invoke-HelmUninstallIfExists -Release (Get-GrafanaReleaseName) -Namespace $env:K8S_NAMESPACE
    Invoke-HelmUninstallIfExists -Release (Get-MetricsReleaseName) -Namespace $env:K8S_NAMESPACE
    Invoke-HelmUninstallIfExists -Release (Get-PromtailReleaseName) -Namespace $env:K8S_NAMESPACE
    Invoke-HelmUninstallIfExists -Release (Get-LokiReleaseName) -Namespace $env:K8S_NAMESPACE
    Invoke-HelmUninstallIfExists -Release $env:K8S_RELEASE_NAME -Namespace $env:K8S_NAMESPACE
    Write-Info 'PostgreSQL PVC retained (StatefulSet volumeClaimTemplates are not removed by Helm uninstall):'
    $pvcs = kubectl get pvc -n $env:K8S_NAMESPACE -o name 2>$null | Where-Object { $_ -match 'rj-postgres-data' }
    if ($pvcs) {
        $pvcs | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host '  (no rj-postgres-data PVC in namespace)'
    }
    Write-Info 'Redeploy: make k8s-deploy-local or make k8s-deploy-all'
}

switch ($Action) {
    'docker-login-ghcr' {
        Invoke-DockerLoginGhcr
    }
    'docker-build' {
        Invoke-DockerBuild
    }
    'docker-build-push-worker' {
        Invoke-DockerBuildPushWorker
    }
    'rollout-worker' {
        Restart-TaskWorker
    }
    'update-worker-image' {
        Update-TaskWorkerImage
    }
    'limit-workers' {
        Limit-KindWorkers
    }
    'namespace' {
        Ensure-Namespace
    }
    'ghcr-secret' {
        Ensure-Namespace
        Ensure-GhcrSecret
    }
    'gcp-sa-secret' {
        Ensure-Namespace
        Ensure-GcpSaSecret
    }
    'helm-install' {
        Ensure-Namespace
        Ensure-GhcrSecret
        Install-Postgres
    }
    'helm-migrate' {
        Ensure-Namespace
        Wait-ForPostgres
        Install-DbMigrate
    }
    'helm-install-worker' {
        Ensure-Namespace
        Ensure-GhcrSecret
        Ensure-GcpSaSecret
        Wait-ForPostgres
        Install-TaskWorker
    }
    'helm-install-promtail' {
        Ensure-Namespace
        Install-Promtail
    }
    'helm-install-loki' {
        Ensure-Namespace
        Install-Loki
    }
    'helm-install-grafana' {
        Ensure-Namespace
        Install-Grafana
    }
    'helm-install-metrics' {
        Ensure-Namespace
        Install-Metrics
        Wait-ForMetrics
        Write-Host 'Metrics stack deployed (Prometheus + node-exporter + kube-state-metrics).'
    }
    'helm-install-logging' {
        Ensure-Namespace
        Install-Loki
        Wait-ForLoki
        Install-Promtail
        Install-Grafana
        Write-Host 'Logging stack deployed (Loki + Promtail + Grafana).'
    }
    'helm-install-observability' {
        Ensure-Namespace
        Install-Loki
        Wait-ForLoki
        Install-Promtail
        Install-Metrics
        Wait-ForMetrics
        Install-Grafana
        Write-Host 'Observability stack deployed (Loki + Promtail + Metrics + Grafana).'
    }
    'deploy' {
        Ensure-Namespace
        Ensure-GhcrSecret
        Install-Postgres
        Wait-ForPostgres
        Install-DbMigrate
        Write-Host "Deployed. Cluster host: $($env:K8S_RELEASE_NAME)-postgres.$($env:K8S_NAMESPACE).svc.cluster.local:5432"
        Write-Host "Local access: make k8s-pg-port-forward  ->  localhost:$($(if ($env:PG_LOCAL_PORT) { $env:PG_LOCAL_PORT } else { '5432' }))"
    }
    'deploy-all' {
        Ensure-Namespace
        Ensure-GhcrSecret
        Ensure-GcpSaSecret
        Install-Postgres
        Wait-ForPostgres
        Install-DbMigrate
        Install-TaskWorker
        Write-Host 'Full stack deployed (postgres + migrate + task-worker).'
    }
    'pg-port-forward' {
        Start-PgPortForward
    }
    'grafana-port-forward' {
        Start-GrafanaPortForward
    }
    'undeploy' {
        Uninstall-AllKeepPgVolume
    }
    'undeploy-keep-pg' {
        Uninstall-AllKeepPgVolume
    }
    'undeploy-apps' {
        Uninstall-WorkerAndMigrate
        Write-Info 'Postgres still running; PVC unchanged'
    }
}
