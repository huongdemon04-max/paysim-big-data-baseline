#!/usr/bin/env bash
set -euo pipefail

BASELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASELINE_DIR"

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Hãy mở Docker Desktop và đợi Docker sẵn sàng, rồi chạy lại start.sh."
  exit 1
fi
if ! docker compose up --help | grep -q -- --wait-timeout; then
  echo "Hãy cập nhật Docker Desktop: cần Docker Compose hỗ trợ --wait-timeout."
  exit 1
fi

DOCKER_ARCH="$(docker info --format '{{.Architecture}}')"
case "$DOCKER_ARCH" in
  aarch64|arm64) export DOCKER_DEFAULT_PLATFORM=linux/arm64 ;;
  x86_64|amd64) export DOCKER_DEFAULT_PLATFORM=linux/amd64 ;;
  *) echo "Kiến trúc Docker chưa được hỗ trợ: $DOCKER_ARCH"; exit 1 ;;
esac
# Prefer the Docker daemon's native CPU even if the user's shell forces AMD64.
DOCKER_MEMORY="$(docker info --format '{{.MemTotal}}')"
COMPOSE=(docker compose -f docker-compose.yml)
if (( DOCKER_MEMORY < 3500000000 )); then
  echo "Docker chỉ có $(( DOCKER_MEMORY / 1024 / 1024 )) MiB RAM. Cấp 4 GB cho Docker Desktop (Resources > Memory), rồi chạy lại."
  exit 1
elif (( DOCKER_MEMORY < 5500000000 )); then
  COMPOSE+=(-f docker-compose.low-memory.yml)
  export COMPOSE_PARALLEL_LIMIT=1
  echo "Docker có $(( DOCKER_MEMORY / 1024 / 1024 )) MiB RAM: dùng chế độ nhẹ cho máy 8 GB (10 events/s, Spark local[1])."
fi

bash ./scripts/prepare-data.sh

collect_diagnostics() {
  {
    echo "PaySim startup diagnostics"
    date -u
    docker version
    docker info --format 'architecture={{.Architecture}} cpus={{.NCPU}} memory={{.MemTotal}}'
    echo "Selected platform: $DOCKER_DEFAULT_PLATFORM"
    echo "Compose files: ${COMPOSE[*]}"
    "${COMPOSE[@]}" ps -a
    local container_id
    while IFS= read -r container_id; do
      [[ -z "$container_id" ]] && continue
      docker inspect --format '{{.Name}} restart={{.RestartCount}} memory_limit={{.HostConfig.Memory}} state={{json .State}} healthcheck={{json .Config.Healthcheck}}' "$container_id"
    done < <("${COMPOSE[@]}" ps -aq)
    "${COMPOSE[@]}" logs --no-color --tail=150
  } > startup-diagnostics.txt 2>&1
  cat startup-diagnostics.txt
  echo "Khởi động chưa thành công. Gửi tệp startup-diagnostics.txt cho giảng viên."
}

echo "Khởi động PaySim trên $DOCKER_DEFAULT_PLATFORM. Lần đầu có thể mất nhiều phút..."
if ! "${COMPOSE[@]}" up -d --build --wait --wait-timeout 1200; then
  collect_diagnostics || true
  exit 1
fi

echo "Hệ thống đã sẵn sàng."
echo "Bảng điều khiển: http://127.0.0.1:8501"
echo "Giao diện HDFS:  http://127.0.0.1:9870"
echo "Giao diện Spark: http://127.0.0.1:4040"
