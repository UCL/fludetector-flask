#! /bin/bash
#
# Fludetector: website, REST API, and data processors for the Fludetector service from UCL.
# (c) 2019, UCL <https://www.ucl.ac.uk/
#
# This file is part of Fludetector
#
# Fludetector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Fludetector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fludetector.  If not, see <http://www.gnu.org/licenses/>.
#
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
