#! /bin/bash
# This script backs up the website's database in production.
#
# Run this from the project's root directory:
#   ./scripts/backup.sh
#
set -e

D=$(date +%Y-%m-%d-%H:%M:%S)

cp data.db /cs/research/fmedia/fmedia12/fludetector-backups/$D-data.db
