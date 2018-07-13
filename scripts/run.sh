#! /bin/bash
# This script runs a model's data collection and analysis. It's a light wrapper
# over the flask script. Mostly to make sure that we're running inside
# the virtual env
#
# Run this from the project's root directory:
#   ./scripts/run.sh MODEL_ID [--start START_DATE] [--end END_DATE] [...]
#
set -e

. venv/bin/activate

export FLASK_APP=./fludetector/app.py

flask "$@"
