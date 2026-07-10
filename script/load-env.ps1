function Import-DbDotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Host "[WARN] Env file not found: $Path (using existing environment)"
        return
    }

    Get-Content -Path $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line -match '^([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    Write-Host "[INFO] Loaded env from $Path"
}

function Get-EnvValue {
    param([string]$Name)
    return [Environment]::GetEnvironmentVariable($Name, 'Process')
}

function Initialize-DbScriptEnv {
  param([string]$ScriptRoot = $PSScriptRoot)

    $envFile = Join-Path $ScriptRoot '.env'
    Import-DbDotEnv -Path $envFile

    $pgDb = Get-EnvValue 'PG_DB'
    if ([string]::IsNullOrWhiteSpace($pgDb)) {
        $pgDb = Get-EnvValue 'PG_DATABASE'
    }

    $pgPassword = Get-EnvValue 'PGPASSWORD'
    if ([string]::IsNullOrWhiteSpace($pgPassword)) {
        $pgPassword = Get-EnvValue 'PG_PASSWORD'
    }

    $pgPort = Get-EnvValue 'PG_PORT'
    if ([string]::IsNullOrWhiteSpace($pgPort)) {
        $pgPort = '5432'
    }

    $pgUser = Get-EnvValue 'PG_USER'
    if ([string]::IsNullOrWhiteSpace($pgUser)) {
        $pgUser = 'postgres'
    }

    $awsKey = Get-EnvValue 'AWS_ACCESS_KEY_ID'
    if ([string]::IsNullOrWhiteSpace($awsKey)) {
        $awsKey = Get-EnvValue 'GCS_HMAC_ACCESS_KEY'
    }

    $awsSecret = Get-EnvValue 'AWS_SECRET_ACCESS_KEY'
    if ([string]::IsNullOrWhiteSpace($awsSecret)) {
        $awsSecret = Get-EnvValue 'GCS_HMAC_SECRET_KEY'
    }

    $awsRegion = Get-EnvValue 'AWS_DEFAULT_REGION'
    if ([string]::IsNullOrWhiteSpace($awsRegion)) {
        $awsRegion = 'auto'
    }

    Set-Item -Path 'env:PG_DB' -Value $pgDb
    Set-Item -Path 'env:PGPASSWORD' -Value $pgPassword
    Set-Item -Path 'env:PG_PORT' -Value $pgPort
    Set-Item -Path 'env:PG_USER' -Value $pgUser
    if (-not [string]::IsNullOrWhiteSpace($awsKey)) {
        Set-Item -Path 'env:AWS_ACCESS_KEY_ID' -Value $awsKey
    }
    if (-not [string]::IsNullOrWhiteSpace($awsSecret)) {
        Set-Item -Path 'env:AWS_SECRET_ACCESS_KEY' -Value $awsSecret
    }
    Set-Item -Path 'env:AWS_DEFAULT_REGION' -Value $awsRegion

    $required = @('PG_HOST', 'PG_USER', 'PG_DB', 'S3_BUCKET', 'PROJECT_NAME', 'APP_ENV', 'TARGET_TABLE')
    $missing = @()
    foreach ($name in $required) {
        if ([string]::IsNullOrWhiteSpace((Get-EnvValue $name))) {
            $missing += $name
        }
    }
    if ([string]::IsNullOrWhiteSpace($pgPassword)) {
        $missing += 'PGPASSWORD (or PG_PASSWORD)'
    }
    if ($missing.Count -gt 0) {
        throw ("Missing required env: " + ($missing -join ', ') + " (set in script/.env or environment)")
    }
}

function Get-AwsS3Args {
    $endpoint = Get-EnvValue 'S3_ENDPOINT'
    if ([string]::IsNullOrWhiteSpace($endpoint)) {
        return @()
    }
    return @('--endpoint-url', $endpoint)
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

function Assert-CommandExists {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name not found in PATH. Install it and retry."
    }
}

function Compress-FileToGzip {
    param(
        [string]$InputPath,
        [string]$OutputPath
    )

    $inputStream = [System.IO.File]::OpenRead($InputPath)
    $outputStream = [System.IO.File]::Create($OutputPath)
    $gzip = New-Object System.IO.Compression.GZipStream(
        $outputStream,
        [System.IO.Compression.CompressionMode]::Compress
    )
    try {
        $inputStream.CopyTo($gzip)
    }
    finally {
        $gzip.Close()
        $inputStream.Close()
        $outputStream.Close()
    }
}

function Expand-GzipToFile {
    param(
        [string]$InputPath,
        [string]$OutputPath
    )

    $inputStream = [System.IO.File]::OpenRead($InputPath)
    $gzip = New-Object System.IO.Compression.GZipStream(
        $inputStream,
        [System.IO.Compression.CompressionMode]::Decompress
    )
    $outputStream = [System.IO.File]::Create($OutputPath)
    try {
        $gzip.CopyTo($outputStream)
    }
    finally {
        $gzip.Close()
        $inputStream.Close()
        $outputStream.Close()
    }
}
