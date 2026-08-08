#!/usr/bin/env bash
set -euo pipefail

BASELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASELINE_DIR"

./scripts/prepare-data.sh

echo "Khởi động hệ thống PaySim Big Data..."
docker compose up -d --build

echo "Đang chờ bảng điều khiển sẵn sàng..."
for _attempt in $(seq 1 120); do
  if curl -fsS http://localhost:8501/_stcore/health >/dev/null 2>&1; then
    echo ""
    echo "Bảng điều khiển: http://127.0.0.1:8501"
    echo "Giao diện HDFS:  http://127.0.0.1:9870"
    echo "Giao diện Spark: http://127.0.0.1:4040"
    exit 0
  fi
  sleep 2
done

echo "Bảng điều khiển chưa sẵn sàng sau 4 phút. Xem nhật ký bằng: docker compose logs --tail=200"
exit 1
