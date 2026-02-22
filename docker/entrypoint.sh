#!/bin/sh
set -e
exec uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8080}" \
    --workers "${WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}"
