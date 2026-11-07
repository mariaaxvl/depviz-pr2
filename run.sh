#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
PY="$(command -v python || command -v python3)"
exec "$PY" src/main.py "$@"
