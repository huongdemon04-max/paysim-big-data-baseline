$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$RootDir = Split-Path -Parent $PSScriptRoot
$DataFile = Join-Path $RootDir "data\paysim.csv"
$DataUrl = "https://github.com/thuanbui1309/paysim-big-data-baseline/releases/download/data-v1/paysim.csv"
$ExpectedSha = "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b"

if (Test-Path $DataFile) {
    $ActualSha = (Get-FileHash $DataFile -Algorithm SHA256).Hash.ToLower()
    if ($ActualSha -eq $ExpectedSha) {
        exit 0
    }
    Write-Error "Tệp PaySim không hợp lệ: $DataFile"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $DataFile) | Out-Null
$TempFile = "$DataFile.download"
Write-Host "Đang tải bộ dữ liệu PaySim..."
# Windows PowerShell 5.1: avoid the Internet Explorer parser/security prompt.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
    for ($Attempt = 1; $Attempt -le 3; $Attempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $DataUrl -OutFile $TempFile -TimeoutSec 600
            break
        } catch {
            if ($Attempt -eq 3) { throw }
            Start-Sleep -Seconds 2
        }
    }
} catch {
    Remove-Item $TempFile -Force -ErrorAction SilentlyContinue
    throw
}
$ActualSha = (Get-FileHash $TempFile -Algorithm SHA256).Hash.ToLower()
if ($ActualSha -ne $ExpectedSha) {
    Remove-Item $TempFile -Force
    Write-Error "Tệp PaySim tải về không hợp lệ."
}
Move-Item $TempFile $DataFile -Force
Write-Host "Bộ dữ liệu PaySim đã sẵn sàng."
