import tempfile
import time
import os
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm.exc import NoResultFound
from apiclient.discovery import build
from googleapiclient.errors import HttpError
from sh import ssh, scp, ErrorReturnCode

from stompest.sync.client import Stomp
from stompest.config import StompConfig
from stompest.protocol import StompSpec

from fludetector.log import logger
from fludetector.models import db, GoogleScore, ModelScore, GoogleLog

from fludetector.calculator import buildCalculator, CalculatorType


def get_google_score(term, day):
    try:
        gs = GoogleScore.query.filter_by(term_id=term.id, day=day).one()
    except NoResultFound:
        gs = GoogleScore()
        gs.day = day
        gs.term = term
    return gs


def collect_google_scores(terms, start, end):
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logger.info('Querying %d terms between %s and %s' % (len(terms), start, end))
    logger.debug(', '.join(t.term for t in terms))
    service = build(
        'trends',
        'v1beta',
        developerKey=os.environ["GOOGLE_API_KEY"],
        discoveryServiceUrl='https://www.googleapis.com/discovery/v1/apis/trends/v1beta/rest',
        cache_discovery=False
    )
    graph = service.getTimelinesForHealth(
        terms=[t.term for t in terms],
        geoRestriction_region='GB-ENG',
        time_startDate=start.strftime('%Y-%m-%d'),
        time_endDate=end.strftime("%Y-%m-%d"),
        timelineResolution='day')
    try:
        response = graph.execute()
    except HttpError as e:
        logger.exception(e)
        raise e
    for line in response['lines']:
        term = next(t for t in terms if t.term == line['term'])
        for point in line['points']:
            day = datetime.strptime(point['date'], "%b %d %Y").date()
            gs = get_google_score(term, day)
            gs.value = float(point['value'])
            yield gs


def send_to_matlab(model, averages):
    fd = tempfile.NamedTemporaryFile()
    fd.write('\n'.join('%s,%f' % a for a in averages))
    fd.flush()

    logger.debug('Sending query list and GoogleScores to fmedia13')
    scp(fd.name, 'fmedia13:/tmp/fludetector_google_matlab_input')
    fd.close()

    fmedia13 = ssh.bake('fmedia13')

    run = ';'.join([
        "fin='/tmp/fludetector_google_matlab_input'",
        "fout='/tmp/fludetector_google_matlab_output'",
        "cd /home/vlampos/website_v2",
        "run('gpml/startup.m')",
        "%s(fin,fout)" % model.get_data()['matlab_function'],
        "exit"])
    logger.debug('Running matlab function over scores')
    fmedia13('matlab', '-nodisplay', '-nojvm', '-r', '"%s"' % run)

    logger.debug('Reading matlab results back')
    value = float(fmedia13('cat', '/tmp/fludetector_google_matlab_output').strip())

    logger.debug('Cleaning up temp files')
    fmedia13('rm', '/tmp/fludetector_google_matlab_input', '/tmp/fludetector_google_matlab_output')

    return value


def calculate_moving_average(term, day, window_size):
    google_scores = term.scores.filter(
        GoogleScore.day > day - timedelta(days=window_size),
        GoogleScore.day <= day).all()
    if len(google_scores) != window_size:
        logger.warn('Not enough data to average %s on %s by %d days' % (term, day, window_size))
        return
    avg = sum(gs.value for gs in google_scores)
    if avg:
        avg = avg / window_size
    return avg


def calculate_moving_averages(model, day):
    window_size = model.get_data()['average_window_size']
    logger.debug('Calculating %d-day averages on %s' % (window_size, day))
    for term in model.google_terms:
        avg = calculate_moving_average(term, day, window_size)
        if avg is None:
            continue
        yield (term.term, avg)


def get_model_score(model, day):
    try:
        ms = ModelScore.query.filter_by(model_id=model.id, day=day, region='e').one()
    except NoResultFound:
        ms = ModelScore()
        ms.region = 'e'
        ms.model = model
        ms.day = day
    return ms


def calculate_score(model, day, engine_runner):
    averages = list(calculate_moving_averages(model, day))
    if not averages:
        return
    ms = get_model_score(model, day)
    try:
        if engine_runner.conf is CalculatorType.LEGACY:
            ms.value = send_to_matlab(model, averages)
        else:
            ms.value = engine_runner.calculateModelScore(model, averages)
    except ErrorReturnCode as e:
        logger.exception(e)
        raise e
    return ms


def get_engine_conf():
    try:
        engine_type = os.environ('MODEL_ENGINE')
        if engine_type == 'matlab':
            conf = CalculatorType.MATLAB
        elif engine_type == 'octave':
            conf = CalculatorType.OCTAVE
        elif engine_type == 'remote':
            conf = CalculatorType.REMOTE
        else:
            conf = CalculatorType.LEGACY
    except KeyError as e:
        conf = CalculatorType.LEGACY
    return conf


def calculate_model_scores(model, start, end):
    logger.info('Calculating new ModelScores between %s and %s' % (start, end))
    days_apart = (end - start).days + 1
    engine_runner = buildCalculator(get_engine_conf())
    days = (start + timedelta(days=d) for d in xrange(days_apart))
    for day in days:
        s = calculate_score(model, day, engine_runner)
        if s:
            yield s


def days_missing_google_score(model, start, end):
    requested = set(start + timedelta(days=i) for i in xrange((end - start).days + 1))
    for term in model.google_terms:
        known = set(s.day for s in term.scores)
        for missing in requested - known:
            yield missing


def days_missing_model_score(model, start, end):
    requested = set(start + timedelta(days=i) for i in xrange((end - start).days + 1))
    known = set(s.day for s in model.scores)
    for missing in requested - known:
        yield missing


def batches(model, start, end):
    max_response = 2000
    max_terms = 30

    terms = model.google_terms.all()
    batch_intervals = xrange(0, len(terms), max_terms)
    for batch_start in batch_intervals:
        batch = terms[batch_start:batch_start + max_terms]

        days_apart = min((end - start).days, max_response // len(batch))
        s, e = start, start + timedelta(days=days_apart)
        while e < end:
            yield batch, s, e
            s, e = e, e + timedelta(days=days_apart)
        yield batch, s, end


def run_batch(batch, start, end):
    delay = 0
    for attempt in xrange(1, 6):
        try:
            for gs in collect_google_scores(batch, start, end):
                db.session.add(gs)
                gl = GoogleLog()
                gl.score_date = gs.day
                gl.score_timestamp = datetime.utcnow()
                db.session.add(gl)
            return
        except HttpError as e:
            if attempt == 6:
                raise e
            delay = 3 ** attempt
            logger.warn('HTTP error on attempt %d, sleeping and trying again in %d seconds' % (attempt, delay))
            time.sleep(delay)


def send_score_to_message_queue(date, score):
    client = Stomp(StompConfig('tcp://fmapiclient.cs.ucl.ac.uk:7672', version=StompSpec.VERSION_1_0))
    client.connect(headers={'passcode': 'admin', 'login': 'admin'})
    message = 'date={0}\nvalue={1}'.format(date, str(score))
    client.send('/queue/PubModelScore.Q', body=message)
    client.disconnect()


def run(model, start, end, **kwargs):
    """
    Run this model between these two dates. Running the model means:
        1) Collecting Google Scores for the model's terms on these days
        2) Using the Google Scores to calculate the Model Scores
    Tries to be clever about when it needs to collect Google Data or not:
        - Find dates between start and end that are missing a GoogleScore for
            at least one of the terms
        - Query for all terms over the smallest date range that covers all
            missing dates.
        - e.g. Same run twice won't hit Google the second time
        - e.g. Two runs that overlap will never query the days in common
        - e.g. Removing a term from a model won't cause extra queries
        - e.g. Adding a term to a model will re-query every term
    """
    logger.info("Run %s model between %s and %s" % (model.name, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))

    needs_collecting = list(days_missing_google_score(model, start, end))
    if needs_collecting:
        # Go back a day to make sure the API can return some data
        # When the dates are near to date.today() you don't get empty responses
        # you get 400s
        window_size = model.get_data()['average_window_size']
        collect_start = min(needs_collecting) - timedelta(days=window_size)
        collect_end = max(needs_collecting)

        batched = list(batches(model, collect_start, collect_end))
        # Assuming 1 second to make and process call with worst case rate limiting
        secs_per_batch = 5 + 3 + 3 ^ 2 + 3 ^ 3 + 3 ^ 4 + 3 ^ 5
        td = timedelta(seconds=len(batched) * secs_per_batch)
        logger.info('Due to rate limiting, querying Google will take at most %s' % str(td))

        for batch, s, e in batched:
            run_batch(batch, s, e)
    else:
        logger.info('GoogleScores already collected')

    msg_date = None
    msg_value = None
    needs_calculating = list(days_missing_model_score(model, start, end))
    if needs_calculating:
        calculate_start = min(needs_calculating)
        calculate_end = max(needs_calculating)

        td = timedelta(seconds=(calculate_end - calculate_start).days * 8)  # Assuming 8 seconds to process each day
        logger.info('To process all days in Matlab/Octave will take roughly %s' % str(td))

        for ms in calculate_model_scores(model, calculate_start, calculate_end):
            db.session.add(ms)
            if os.environ['TWITTER_ENABLED'] == 'True':
                msg_date = ms.day
                msg_value = ms.value
    else:
        logger.info('ModelScores already calculated')

    db.session.commit()
    if msg_date is not None and msg_value is not None:
        send_score_to_message_queue(msg_date, msg_value)
        logger.info('Latest ModelScore value sent to message queue')
