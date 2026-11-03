#!/bin/sh
# Start the read-only API. Without a mounted warehouse, fetch the latest release asset.
set -e
if [ ! -f "$WAREHOUSE_PATH" ]; then
  echo "No warehouse at $WAREHOUSE_PATH — downloading $WAREHOUSE_URL"
  mkdir -p "$(dirname "$WAREHOUSE_PATH")"
  curl -fsSL "$WAREHOUSE_URL" -o "$WAREHOUSE_PATH"
fi
exec /app/.venv/bin/uvicorn app.main:app_from_env --factory --app-dir /app/api \
  --host 0.0.0.0 --port 8000
