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
    $ComposeArgs = @('compose', '-f', 'docker-compose.yml')
    $DockerMemoryMiB = [math]::Floor([long]$DockerMemory / 1MB)
    if ([long]$DockerMemory -lt 3500000000) {
        throw "Docker chỉ có $DockerMemoryMiB MiB RAM. Cấp 4 GB cho Docker Desktop/WSL, rồi chạy lại."
    } elseif ([long]$DockerMemory -lt 5500000000) {
        $ComposeArgs += @('-f', 'docker-compose.low-memory.yml')
        $env:COMPOSE_PARALLEL_LIMIT = '1'
        Write-Host "Docker có $DockerMemoryMiB MiB RAM: dùng chế độ nhẹ cho máy 8 GB (10 events/s, Spark local[1])."
    }

    docker @ComposeArgs config --quiet
    if ($LASTEXITCODE -ne 0) { throw "Cấu hình Compose không hợp lệ. Kiểm tra .env và đường dẫn dữ liệu." }

    powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\prepare-data.ps1"
    if ($LASTEXITCODE -ne 0) { throw "Không thể chuẩn bị bộ dữ liệu PaySim." }

    Write-Host "Khởi động PaySim trên $env:DOCKER_DEFAULT_PLATFORM. Lần đầu có thể mất nhiều phút..."
    # PowerShell 5.1 turns native stderr into ErrorRecord objects; keep collecting.
    $ErrorActionPreference = 'Continue'
    docker @ComposeArgs up -d --build --wait --wait-timeout 1200 2>&1 | Tee-Object -FilePath startup-output.log
    $StartupExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($StartupExitCode -ne 0) {
        # Native commands can write to stderr; retain that output in the report.
        $ErrorActionPreference = 'Continue'
        & {
            'PaySim startup diagnostics'
            "Compose startup exit code: $StartupExitCode"
            'Build/start output:'
            Get-Content startup-output.log
            Get-Date -Format o
            docker version
            docker info --format 'architecture={{.Architecture}} cpus={{.NCPU}} memory={{.MemTotal}}'
            "Selected platform: $env:DOCKER_DEFAULT_PLATFORM"
            "Compose files: $ComposeArgs"
            docker @ComposeArgs images
            docker @ComposeArgs ps -a
            $ContainerIds = docker @ComposeArgs ps -aq
            foreach ($ContainerId in $ContainerIds) {
                docker inspect --format '{{.Name}} restart={{.RestartCount}} memory_limit={{.HostConfig.Memory}} state={{json .State}} healthcheck={{json .Config.Healthcheck}}' $ContainerId
            }
            docker @ComposeArgs logs --no-color --tail=150
        } *> startup-diagnostics.txt
        Write-Host 'Khởi động chưa thành công. Chi tiết được lưu tại startup-diagnostics.txt.'
        exit 1
    }

    Write-Host 'Hệ thống đã sẵn sàng.'
    Write-Host 'Bảng điều khiển: http://127.0.0.1:8501'
    Write-Host 'Giao diện HDFS:  http://127.0.0.1:9870'
    Write-Host 'Giao diện Spark: http://127.0.0.1:4040'
    # Browser launch is optional; a browser association error must not report Docker failure.
    try { Start-Process 'http://127.0.0.1:8501' } catch {
        Write-Host 'Mở trình duyệt tại http://127.0.0.1:8501'
    }
} catch {
    Write-Host $_.Exception.Message
    exit 1
}
