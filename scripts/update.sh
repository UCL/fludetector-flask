#! /bin/bash
# This script updates the local deployment, it's for use in the production
# environment, developers should be able to deploy manually.
#
# Run this from the project's root directory:
#   ./scripts/update.sh
#
set -e

git pull origin master

. venv/bin/activate
export PYTHONPATH="$PYTHONPATH:$PWD"
pip install -r requirements.txt

alembic upgrade head

supervisorctl restart fludetector
