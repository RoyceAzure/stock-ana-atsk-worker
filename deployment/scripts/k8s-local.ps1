param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('namespace', 'ghcr-secret', 'helm-install', 'deploy', 'undeploy')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '../..')
$EnvFile = Join-Path $ProjectRoot '.env'
$ChartPath = Join-Path $ProjectRoot 'deployment/helm/charts/postgres'

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
    'deploy' {
        Ensure-Namespace
        Ensure-GhcrSecret
        Install-Postgres
        Write-Host "Deployed. Postgres host: $($env:K8S_RELEASE_NAME)-postgres.$($env:K8S_NAMESPACE).svc.cluster.local:5432"
    }
    'undeploy' {
        Require-EnvVar 'K8S_RELEASE_NAME'
        Require-EnvVar 'K8S_NAMESPACE'
        helm uninstall $env:K8S_RELEASE_NAME --namespace $env:K8S_NAMESPACE
    }
}
