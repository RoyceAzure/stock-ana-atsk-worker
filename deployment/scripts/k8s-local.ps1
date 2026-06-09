param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('namespace', 'ghcr-secret', 'helm-install', 'helm-migrate', 'deploy', 'undeploy', 'pg-port-forward')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '../..')
$EnvFile = Join-Path $ProjectRoot '.env'
$ChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/postgres'
$MigrateChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/db-migrate'
$MigrationsSrc = Join-Path $ProjectRoot 'deployment/db/migrations'

function Load-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw ".env not found at $Path"
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line -match '^([^=]+)=(.*)$') {
            Set-Item -Path "env:$($matches[1].Trim())" -Value $matches[2].Trim()
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

function Install-Postgres {
    Require-EnvVar 'K8S_RELEASE_NAME'
    Require-EnvVar 'K8S_NAMESPACE'
    helm upgrade --install $env:K8S_RELEASE_NAME $ChartPath `
        --namespace $env:K8S_NAMESPACE `
        --set "imagePullSecretName=$GhcrSecretName"
}

function Get-MigrateReleaseName {
    Require-EnvVar 'K8S_RELEASE_NAME'
    return "$($env:K8S_RELEASE_NAME)-migrate"
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
    helm upgrade --install $migrateRelease $MigrateChartPath `
        --namespace $env:K8S_NAMESPACE `
        --set "postgres.releaseName=$($env:K8S_RELEASE_NAME)" `
        --set "imagePullSecretName=$GhcrSecretName" `
        --wait --timeout 5m
    Write-Host "Migration job completed (golang-migrate up is idempotent)."
}

function Start-PgPortForward {
    Require-EnvVar 'K8S_RELEASE_NAME'
    Require-EnvVar 'K8S_NAMESPACE'
    $localPort = if ($env:PG_LOCAL_PORT) { $env:PG_LOCAL_PORT } else { '5432' }
    $svc = "$($env:K8S_RELEASE_NAME)-postgres"
    Write-Host "Forwarding localhost:${localPort} -> ${svc}.${env:K8S_NAMESPACE}:5432 (Ctrl+C to stop)"
    kubectl port-forward -n $env:K8S_NAMESPACE "svc/$svc" "${localPort}:5432"
}

switch ($Action) {
    'namespace' {
        Ensure-Namespace
    }
    'ghcr-secret' {
        Ensure-Namespace
        Ensure-GhcrSecret
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
    'deploy' {
        Ensure-Namespace
        Ensure-GhcrSecret
        Install-Postgres
        Wait-ForPostgres
        Install-DbMigrate
        Write-Host "Deployed. Cluster host: $($env:K8S_RELEASE_NAME)-postgres.$($env:K8S_NAMESPACE).svc.cluster.local:5432"
        Write-Host "Local access: make k8s-pg-port-forward  ->  localhost:$($(if ($env:PG_LOCAL_PORT) { $env:PG_LOCAL_PORT } else { '5432' }))"
    }
    'pg-port-forward' {
        Start-PgPortForward
    }
    'undeploy' {
        Require-EnvVar 'K8S_RELEASE_NAME'
        Require-EnvVar 'K8S_NAMESPACE'
        $migrateRelease = Get-MigrateReleaseName
        helm uninstall $migrateRelease --namespace $env:K8S_NAMESPACE 2>$null
        helm uninstall $env:K8S_RELEASE_NAME --namespace $env:K8S_NAMESPACE
    }
}
