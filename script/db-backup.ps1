$ErrorActionPreference = 'Stop'

. "$PSScriptRoot/load-env.ps1"
Initialize-DbScriptEnv -ScriptRoot $PSScriptRoot

Assert-CommandExists -Name 'pg_dump'
Assert-CommandExists -Name 'aws'

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$fileName = "$($env:TARGET_TABLE)_${timestamp}.sql.gz"
$s3Prefix = "$($env:PROJECT_NAME)/$($env:APP_ENV)/db-backup/$($env:TARGET_TABLE)"
$s3Path = "s3://$($env:S3_BUCKET)/${s3Prefix}/${fileName}"
$awsArgs = Get-AwsS3Args

$sqlFile = Join-Path $env:TEMP "db-backup-$([guid]::NewGuid().ToString()).sql"
$gzipFile = "${sqlFile}.gz"

try {
    Write-Host "[START] Backing up table: $($env:TARGET_TABLE) from postgres..."
    Write-Host "[UPLOAD] Streaming backup directly to ${s3Path}..."

    Invoke-External -FilePath pg_dump -ArgumentList @(
        '-h', $env:PG_HOST,
        '-p', $env:PG_PORT,
        '-U', $env:PG_USER,
        '-d', $env:PG_DB,
        '-t', $env:TARGET_TABLE,
        '-a',
        '-f', $sqlFile
    )

    Compress-FileToGzip -InputPath $sqlFile -OutputPath $gzipFile
    Invoke-External -FilePath aws -ArgumentList (@('s3', 'cp', $gzipFile, $s3Path) + $awsArgs)

    Write-Host '[SUCCESS] Backup completed and uploaded to S3.'
}
finally {
    if (Test-Path $sqlFile) { Remove-Item $sqlFile -Force }
    if (Test-Path $gzipFile) { Remove-Item $gzipFile -Force }
}
