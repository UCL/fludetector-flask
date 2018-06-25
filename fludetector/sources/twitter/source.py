import os
from datetime import timedelta

import sh
from sh import cat, lzop, ssh, scp

from fludetector.errors import FluDetectorError
from fludetector.log import logger
from fludetector.models import db

SINGLE_DAY_COMBINED_PATH = '/tmp/fludetector_twitter_single_day_combined'
SINGLE_DAY_PATH = '/tmp/fludetector_twitter_single_day'
SHREW_OUTPUT_PATH = '/tmp/fludetector_twitter_shrew_output'


def input0(day):
    day_before = day - timedelta(days=1)
    return '/cs/research/fmedia/fmedia12/twitterStream/geofilter/{}-23'.format(day_before.strftime('%Y%m%d'))


def input1(day):
    return '/cs/research/fmedia/fmedia12/twitterStream/geofilter/archive/{}.lzo'.format(day.strftime('%Y%m%d'))


def input2(day):
    day_after = day + timedelta(days=1)
    return '/cs/research/fmedia/fmedia12/twitterStream/geofilter/{}-00'.format(day_after.strftime('%Y%m%d'))


def collect_tweets(day):
    logger.debug('Collecting Tweets for %s' % day.strftime('%Y-%m-%d'))

    if not os.path.isfile(input0(day)):
        raise FluDetectorError("Couldn't find tweets from %s" % input0(day))

    if not os.path.isfile(input2(day)):
        raise FluDetectorError("Couldn't find tweets from %s" % input2(day))

    path = input1(day)
    if not os.path.isfile(path):
        raise FluDetectorError("Couldn't find tweets from %s" % path)
    logger.debug("  Decompressing day's Tweets")
    lzop(
        '--decompress', path,
        '--output', SINGLE_DAY_PATH,
        '--force'
    )


def shrew(day):
    logger.debug('Running Shrew over Tweets from %s' % day.strftime('%Y-%m-%d'))
    cmd = sh.Command('/home/deploy/shrew/shrew')
    cmd(
        'run',
        '/home/deploy/fludetector/fludetector/sources/twitter/shrew-profile.yaml',
        '--as', 'local',
        '--day', day.strftime('%Y%m%d'),
        '--input0', input0(day),
        '--input1', input1(day),
        '--input2', input2(day),
        '--output', SHREW_OUTPUT_PATH)


def calculate_twitter_scores(model, start, end):
    start = start - timedelta(days=7)  # Go back an extra week so we can average over 7 days
    date_range = [start + timedelta(days=i) for i in xrange((end - start).days)]
    for day in date_range:
        try:
            collect_tweets(day)
            shrew(day)
        except FluDetectorError as e:
            logger.warn(e.message)
        except sh.ErrorReturnCode_1 as e:
            logger.error(e.stdout)
    return []


def calculate_model_scores(model, start, end):
    return []


def days_missing_twitter_score(model, start, end):
    requested = set(start + timedelta(days=i) for i in xrange((end - start).days))
    for ngram in model.twitter_ngrams:
        known = set(s.day for s in ngram.scores)
        for missing in requested - known:
            yield missing


def days_missing_model_score(model, start, end):
    requested = set(start + timedelta(days=i) for i in xrange((end - start).days))
    known = set(s.day for s in model.scores)
    for missing in requested - known:
        yield missing


def run(model, start, end, **kwargs):
    # For each day in date range
        # for each day in day and previous week
            # Collect tweets
                # include hour's padding each side of each day
            # Run shrew over tweets
            # For each region
                # Run region's ngramcounter over tweets
        # For each region
            # Normalise scores over the week
            # Send normalised scores to matlab
    logger.info("Run %s model between %s and %s" % (model.name, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))

    missing_twitter_score = list(days_missing_twitter_score(model, start, end))
    if missing_twitter_score:
        s = min(missing_twitter_score)
        e = max(missing_twitter_score)
        logger.info('Calculating TwitterScores between %s and %s' % (s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')))
        for ts in calculate_twitter_scores(model, s, e):
            db.session.add(ts)
    else:
        logger.info('TwitterScores already calculated')

    missing_model_score = list(days_missing_model_score(model, start, end))
    if missing_model_score:
        s = min(missing_model_score)
        e = max(missing_model_score)
        for ms in calculate_model_scores(model, s, e):
            db.session.add(ms)
    else:
        logger.info('ModelScores already calculated')

    db.session.commit()
