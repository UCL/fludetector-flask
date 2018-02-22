#! /bin/bash
# This script runs gunicorn, use it to serve the website in production mode
# Supervisor uses this script to keep the website running
#
# Run this from the project's root directory:
#   ./scripts/serve.sh
#
set -e

. venv/bin/activate
export PYTHONPATH="$PYTHONPATH:$PWD"

gunicorn \
    --bind 0.0.0.0:5002 \
    --workers 4 \
    --access-logfile logs/gunicorn.access.log \
    --error-logfile logs/gunicorn.error.log \
    fludetector.app:app
