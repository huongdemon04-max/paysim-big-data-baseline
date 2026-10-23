#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Lệnh này xóa dữ liệu Docker của riêng baseline PaySim: Kafka, HDFS và MongoDB."
read -r -p "Nhập RESET để tiếp tục: " CONFIRMATION
if [[ "$CONFIRMATION" != "RESET" ]]; then
  echo "Đã hủy."
  exit 0
fi

docker compose -f docker-compose.yml down -v --remove-orphans
echo "Hệ thống đã được đặt lại. Tệp paysim.csv gốc không bị thay đổi."
