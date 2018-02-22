import csv
from datetime import datetime

from sqlalchemy.orm.exc import NoResultFound

from fludetector.log import logger
from fludetector.errors import FluDetectorError
from fludetector.models import db, REGIONS, ModelScore


def find_matching_index(headers, possible, required=False):
    for i, h in enumerate(headers):
        if h in possible:
            return i
    if required:
        e = FluDetectorError('No %s header in CSV file' % ','.join(possible))
        logger.exception(e)
        raise e


def find_region_index(headers):
    indexes = {}
    for code, name in REGIONS.iteritems():
        index = find_matching_index(headers, [code, name])
        if index:
            indexes[code] = index
    if not indexes:
        e = FluDetectorError('No region headers found')
        logger.exception(e)
        raise e
    return indexes


def run(model, start, end, csv_file=None, **kwargs):
    if csv_file is None:
        raise FluDetectorError('No CSV file provided')
    logger.info('Reading CSV file into %s' % str(model))
    csv_reader = csv.reader(csv_file)

    headers = next(csv_reader)

    day_index = find_matching_index(headers, ['Day', 'Date'], required=True)
    region_index = find_region_index(headers)

    logger.debug('Found columns for regions %s' % ', '.join(region_index.keys()))

    logger.info('Reading rows...')
    for row_index, row in enumerate(csv_reader):
        day = datetime.strptime(row[day_index], '%Y-%m-%d').date()

        if day < start or day > end:
            continue

        for region, col_index in region_index.iteritems():
            try:
                value = float(row[col_index])
            except ValueError:
                logger.debug('Skipping row %d column %d, not a float' % (row_index + 1, col_index))
                continue
            try:
                ms = ModelScore.query.filter_by(model_id=model.id, day=day, region=region).one()
            except NoResultFound:
                ms = ModelScore()
                ms.region = region
                ms.model = model
                ms.day = day
            ms.value = value
            db.session.add(ms)

    db.session.commit()
    logger.info('Done!')
