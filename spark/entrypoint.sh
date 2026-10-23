#!/usr/bin/env sh
set -eu
# A container restart retains /tmp. Readiness belongs to the NEW Spark process.
rm -f /tmp/pipeline-ready
exec /opt/entrypoint.sh "$@"
