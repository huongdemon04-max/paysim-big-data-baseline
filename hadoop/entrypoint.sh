#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == hdfs && "${2:-}" == namenode ]]; then
  if [[ ! -f /data/name/current/VERSION ]]; then
    # A partial format must not silently overwrite recoverable HDFS metadata.
    if [[ -n "$(find /data/name -mindepth 1 -maxdepth 1 ! -name lost+found -print -quit)" ]]; then
      echo "HDFS: /data/name contains data but current/VERSION is missing. Refusing to format; inspect the volume before recovery." >&2
      exit 1
    fi
    hdfs namenode -format -nonInteractive
  fi
fi

exec "$@"
