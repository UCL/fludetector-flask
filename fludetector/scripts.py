"""
Fludetector: website, REST API, and data processors for the Fludetector service from UCL.
(c) 2019, UCL <https://www.ucl.ac.uk/

This file is part of Fludetector

Fludetector is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fludetector is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fludetector.  If not, see <http://www.gnu.org/licenses/>.
"""
from datetime import datetime, date, timedelta

import click
from sqlalchemy.orm.exc import NoResultFound

from fludetector.sources import google, csv_, twitter
from fludetector.errors import FluDetectorError
from fludetector.models import db, Model

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import logging

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

MODEL_TYPES = {
    'google': google,
    'twitter': twitter,
    'csv': csv_
}


def initdb():
    """Initialize the database."""
    db.create_all()


def listmodels():
    """List all models"""
    for m in Model.query.all():
        click.echo('%d) %s (%s)' % (m.id, m.name, 'Public' if m.public else 'Private'))


@click.argument('model_id', type=int)
@click.option('-s', '--start', help='Collect data from (including) this day (YYYY-MM-DD) (defaults to the day after the most recent score)')
@click.option('-e', '--end', help='Collect data up to (not including) this day (YYYY-MM-DD) (defaults to 2 days ago)')
@click.option('--csv', help='The CSV file with data to analyse (used for CSV-type models)', type=click.File('rb'))
def runmodel(model_id, start, end, csv):
    """Collect data and run model over them"""
    try:
        model = Model.query.filter_by(id=model_id).one()

        if start:
            start = datetime.strptime(start, '%Y-%m-%d').date()
        else:
            start = model.last_score.day + timedelta(days=1)

        if end:
            end = datetime.strptime(end, '%Y-%m-%d').date()
        else:
            end = date.today() - timedelta(days=2)

        if start > end:
            raise click.ClickException('Start must be before end')
        if end >= date.today():
            raise click.ClickException('End must be in the past')

        MODEL_TYPES[model.type].run(model, start, end, csv_file=csv)
    except NoResultFound:
        raise click.ClickException('Could not find model with that ID')
    except FluDetectorError as e:
        raise click.ClickException(e.message)


def init_app(app):
    command = app.cli.command()
    command(initdb)
    command(listmodels)
    command(runmodel)
    command(runmodelscheduler)


def runmodel_func(model_id):
    from fludetector.app import app
    with app.app_context():
        try:
            model = Model.query.filter_by(id=model_id).one()
            start = model.last_score.day + timedelta(days=1)
            end = date.today() - timedelta(days=2)
            MODEL_TYPES[model.type].run(model, start, end, csv_file=None)
        except NoResultFound:
            raise click.ClickException('Could not find model with that ID')
        except FluDetectorError as e:
            raise click.ClickException(e.message)


@click.argument('model_id', type=int)
@click.argument('crontab', type=str)
def runmodelscheduler(model_id, crontab):
    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=runmodel_func,
        kwargs={"model_id": model_id},
        trigger=CronTrigger.from_crontab(crontab),
        misfire_grace_time=3600)
    scheduler.start()
