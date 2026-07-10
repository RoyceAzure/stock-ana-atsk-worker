$ErrorActionPreference = 'Stop'

. "$PSScriptRoot/load-env.ps1"
Initialize-DbScriptEnv -ScriptRoot $PSScriptRoot

Assert-CommandExists -Name 'psql'
Assert-CommandExists -Name 'aws'

$s3Prefix = "$($env:PROJECT_NAME)/$($env:APP_ENV)/db-backup/$($env:TARGET_TABLE)"
$s3SearchPath = "s3://$($env:S3_BUCKET)/${s3Prefix}/"
$awsArgs = Get-AwsS3Args

Write-Host "[INFO] Searching for backups in: ${s3SearchPath}"

$listOutput = & aws s3 ls $s3SearchPath @awsArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    throw ("aws s3 ls failed (exit $LASTEXITCODE): " + ($listOutput -join "`n"))
}

$latestLine = $listOutput |
    Where-Object { $_ -and ($_ -is [string]) -and $_.Trim() } |
    Sort-Object |
    Select-Object -Last 1

if ([string]::IsNullOrWhiteSpace($latestLine)) {
    Write-Host "[ERROR] No backup files found in ${s3SearchPath}"
    Write-Host 'Please check if S3 path exists or TARGET_TABLE name is correct.'
    exit 1
}

$latestFile = ($latestLine.Trim() -split '\s+', 4)[3]
if ([string]::IsNullOrWhiteSpace($latestFile)) {
    throw "Failed to parse latest backup filename from: $latestLine"
}

Write-Host "[START] Found latest backup: $latestFile"
Write-Host "[START] Restoring into table: $($env:TARGET_TABLE)..."

$gzipFile = Join-Path $env:TEMP "db-restore-$([guid]::NewGuid().ToString()).sql.gz"
$sqlFile = Join-Path $env:TEMP "db-restore-$([guid]::NewGuid().ToString()).sql"

try {
    Invoke-External -FilePath aws -ArgumentList (@(
        's3', 'cp', "${s3SearchPath}${latestFile}", $gzipFile
    ) + $awsArgs)

    Expand-GzipToFile -InputPath $gzipFile -OutputPath $sqlFile

    Write-Host '[START] Truncating table...'
    Invoke-External -FilePath psql -ArgumentList @(
        '-h', $env:PG_HOST,
        '-p', $env:PG_PORT,
        '-U', $env:PG_USER,
        '-d', $env:PG_DB,
        '-c', "TRUNCATE TABLE $($env:TARGET_TABLE);"
    )

    Write-Host '[START] Importing data from SQL dump...'
    Invoke-External -FilePath psql -ArgumentList @(
        '-h', $env:PG_HOST,
        '-p', $env:PG_PORT,
        '-U', $env:PG_USER,
        '-d', $env:PG_DB,
        '-f', $sqlFile
    )

    Write-Host "[SUCCESS] Restore completed for table: $($env:TARGET_TABLE)"
}
finally {
    if (Test-Path $gzipFile) { Remove-Item $gzipFile -Force }
    if (Test-Path $sqlFile) { Remove-Item $sqlFile -Force }
}
