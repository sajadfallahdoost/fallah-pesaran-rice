#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
set -- -f compose.https.yaml "$@"
if [ -f compose.override.yaml ]; then
    set -- -f compose.override.yaml "$@"
fi
exec docker compose --env-file .env.production -f compose.yaml "$@"
