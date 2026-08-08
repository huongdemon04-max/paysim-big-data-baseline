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
Invoke-WebRequest -Uri $DataUrl -OutFile $TempFile
$ActualSha = (Get-FileHash $TempFile -Algorithm SHA256).Hash.ToLower()
if ($ActualSha -ne $ExpectedSha) {
    Remove-Item $TempFile -Force
    Write-Error "Tệp PaySim tải về không hợp lệ."
}
Move-Item $TempFile $DataFile -Force
Write-Host "Bộ dữ liệu PaySim đã sẵn sàng."
