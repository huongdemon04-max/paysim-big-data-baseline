#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_FILE="$ROOT_DIR/data/paysim.csv"
DATA_URL="https://github.com/thuanbui1309/paysim-big-data-baseline/releases/download/data-v1/paysim.csv"
EXPECTED_SHA="16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b"

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d ' ' -f 1
  else
    shasum -a 256 "$1" | cut -d ' ' -f 1
  fi
}

if [[ -f "$DATA_FILE" ]]; then
  ACTUAL_SHA="$(hash_file "$DATA_FILE")"
  if [[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]]; then
    exit 0
  fi
  echo "Tệp PaySim không hợp lệ: $DATA_FILE"
  exit 1
fi

mkdir -p "$ROOT_DIR/data"
TEMP_FILE="$DATA_FILE.download"
echo "Đang tải bộ dữ liệu PaySim..."
trap 'rm -f "$TEMP_FILE"' EXIT
curl -fL --retry 3 --connect-timeout 30 --max-time 1800 --progress-bar "$DATA_URL" -o "$TEMP_FILE"
ACTUAL_SHA="$(hash_file "$TEMP_FILE")"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  rm -f "$TEMP_FILE"
  echo "Tệp PaySim tải về không hợp lệ."
  exit 1
fi
mv "$TEMP_FILE" "$DATA_FILE"
echo "Bộ dữ liệu PaySim đã sẵn sàng."
