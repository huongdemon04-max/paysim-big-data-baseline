$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Hãy cài và mở Docker Desktop, rồi chạy lại start.bat."
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Hãy mở Docker Desktop và đợi Docker sẵn sàng, rồi chạy lại start.bat."
    }
    $ComposeHelp = docker compose up --help | Out-String
    if ($LASTEXITCODE -ne 0 -or $ComposeHelp -notmatch '--wait-timeout') {
        throw "Hãy cập nhật Docker Desktop: cần Docker Compose hỗ trợ --wait-timeout."
    }
    $DockerArch = docker info --format '{{.Architecture}}'
    switch ($DockerArch.Trim()) {
        { $_ -in 'aarch64', 'arm64' } { $env:DOCKER_DEFAULT_PLATFORM = 'linux/arm64' }
        { $_ -in 'x86_64', 'amd64' } { $env:DOCKER_DEFAULT_PLATFORM = 'linux/amd64' }
        default { throw "Kiến trúc Docker chưa được hỗ trợ: $DockerArch" }
    }
    $DockerMemory = docker info --format '{{.MemTotal}}'
    if ([long]$DockerMemory -lt 5500000000) {
        throw "Docker chưa đủ RAM. Cấp ít nhất 6 GB cho Docker Desktop/WSL, rồi chạy lại."
    }

    powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\prepare-data.ps1"
    if ($LASTEXITCODE -ne 0) { throw "Không thể chuẩn bị bộ dữ liệu PaySim." }

    Write-Host "Khởi động PaySim trên $env:DOCKER_DEFAULT_PLATFORM. Lần đầu có thể mất nhiều phút..."
    docker compose up -d --build --wait --wait-timeout 1200
    if ($LASTEXITCODE -ne 0) {
        # Native commands can write to stderr; retain that output in the report.
        $ErrorActionPreference = 'Continue'
        & {
            'PaySim startup diagnostics'
            Get-Date -Format o
            docker version
            docker info --format 'architecture={{.Architecture}} cpus={{.NCPU}} memory={{.MemTotal}}'
            "Selected platform: $env:DOCKER_DEFAULT_PLATFORM"
            docker compose ps -a
            $ContainerIds = docker compose ps -aq namenode datanode
            foreach ($ContainerId in $ContainerIds) {
                docker inspect --format '{{.Name}} restart={{.RestartCount}} state={{json .State}} healthcheck={{json .Config.Healthcheck}}' $ContainerId
            }
            docker compose logs --no-color --tail=150 hdfs-init namenode datanode kafka spark
        } *> startup-diagnostics.txt
        Get-Content startup-diagnostics.txt
        Write-Host 'Khởi động chưa thành công. Gửi tệp startup-diagnostics.txt cho giảng viên.'
        exit 1
    }

    Write-Host 'Hệ thống đã sẵn sàng.'
    Write-Host 'Bảng điều khiển: http://127.0.0.1:8501'
    Write-Host 'Giao diện HDFS:  http://127.0.0.1:9870'
    Write-Host 'Giao diện Spark: http://127.0.0.1:4040'
    Start-Process 'http://127.0.0.1:8501'
} catch {
    Write-Host $_.Exception.Message
    exit 1
}
