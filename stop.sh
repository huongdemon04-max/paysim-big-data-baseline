#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker compose -f docker-compose.yml stop
echo "Đã dừng hệ thống."
