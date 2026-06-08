#!/bin/sh
set -e

# Start Flask with gunicorn in background
cd /app/backend
gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 120 "app:create_app()" &

# Start nginx in foreground
nginx -g "daemon off;"
