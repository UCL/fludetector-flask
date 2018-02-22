#! /bin/bash
# This script bootstraps the project after a fresh clone. Useful for new
# developers, or in new deployments.
#
# Run this from the project's root directory:
#   ./scripts/init.sh
#
set -e
export FLASK_APP=./fludetector/app.py

. venv/bin/activate
export PYTHONPATH="$PYTHONPATH:$PWD"
pip install -r requirements.txt

flask initdb
alembic upgrade head
