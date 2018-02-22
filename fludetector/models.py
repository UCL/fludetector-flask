from datetime import timedelta

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

REGIONS = {
    'e': 'England',
    's': 'South England',
    'm': 'Midlands',
    'l': 'London',
    'n': 'North England'
}


def get_region(code):
    return {'code': code, 'name': REGIONS[code]}


class Model(db.Model):
    """The base class for storing model data.

    name - This is presented in the admin and public sites, as well as the API
    type - So we know how to collect and analyse the data
    public - Whether or not we should show this model's data in the public site and API
    data - A string that can hold whatever data this model/type requires

    """
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Text, unique=True, index=True, nullable=False)
    type = db.Column(db.Text, nullable=False)
    public = db.Column(db.Boolean, nullable=False)
    data = db.Column(db.Text, nullable=True)

    @property
    def regions(self):
        """Returns a list of the regions that this model has scores for"""
        codes = set(s.region for s in self.scores)
        return [get_region(c) for c in codes]

    @property
    def first_score(self):
        """Return the earliest ModelScore for this model.
        Useful for pre-filling the start date box in the filter form"""
        return self.scores.order_by(ModelScore.day.asc()).first()

    @property
    def last_score(self):
        """Return the latest ModelScore for this model.
        Useful for pre-filling the end date box in the filter form"""
        return self.scores.order_by(ModelScore.day.desc()).first()

    def scores_for(self, region):
        """Return all the ModelScores for this region"""
        return self.scores.filter_by(region=region)

    def get_scores(self, start, end, region, resolution):
        """Get the ModelScores that match the arguments

        start - Only scores for this day onwards
        end - Only scores up to (not including) this day
        region - Only scores in this region
        resolution - Default daily, if 'week' then only return scores from Sundays

        """
        scores = self.scores.filter(
            ModelScore.day >= start,
            ModelScore.day < end,
            ModelScore.region == region).all()

        if resolution == 'week':
            scores = [s for s in scores if s.day.weekday() == 6]

        return scores

    def get_data(self):
        """Parse this model's data attribute and return a dict"""
        if self.type in ['google', 'twitter']:
            matlab_function, average_window_size = self.data.split(',')
            return {
                'matlab_function': matlab_function,
                'average_window_size': int(average_window_size)
            }

    def __setattr__(self, name, value):
        """This is used to intercept the WTForms populate_obj method's setting
        of special model values.

        It saves certain attributes into the data attribute so that it can be
        saved to the databse"""

        if name == 'matlab_function':
            data = (self.data or ',').split(',')
            self.data = '%s,%s' % (value, str(data[1]))
            return
        if name == 'average_window_size':
            data = (self.data or ',').split(',')
            self.data = '%s,%s' % (data[0], str(value))
            return

        super(Model, self).__setattr__(name, value)

    def __repr__(self):
        return '<Model %s>' % self.name


class ModelScore(db.Model):
    """Represents a fully analysed score for a model in a single region on a single day"""
    day = db.Column(db.Date, primary_key=True, nullable=False)
    region = db.Column(db.Text, primary_key=True, nullable=False)
    value = db.Column(db.Float, nullable=False)

    model_id = db.Column(
        db.Integer, db.ForeignKey('model.id'), primary_key=True, nullable=False)
    model = db.relationship(
        'Model',
        backref=db.backref('scores', lazy='dynamic', cascade='all,delete,delete-orphan'))

    def smoothed(self, days):
        range = timedelta(days=max(0, (days - 1) / 2))
        scores = self.model.scores.filter(
            ModelScore.day >= self.day - range,
            ModelScore.day <= self.day + range,
            ModelScore.region == self.region).all()
        return sum(s.value for s in scores) / len(scores)

    def __repr__(self):
        return '<ModelScore %s %s %f>' % (
            self.day.strftime('%Y-%m-%d'), self.region, self.value)


model_google_terms = db.Table(
    'model_google_terms',
    db.Column('model_id', db.Integer, db.ForeignKey('model.id'), nullable=False),
    db.Column('google_term_id', db.Integer, db.ForeignKey('google_term.id'), nullable=False)
)


class GoogleTerm(db.Model):
    """A search query term that a Google-type model might use"""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    term = db.Column(db.Text, unique=True, index=True, nullable=False)

    models = db.relationship(
        'Model',
        secondary=model_google_terms,
        backref=db.backref('google_terms', lazy='dynamic'))

    def __repr__(self):
        return '<GoogleTerm %s>' % self.term


class GoogleScore(db.Model):
    """A raw score from Google for a GoogleTerm on a single day"""
    day = db.Column(db.Date, primary_key=True, nullable=False)
    value = db.Column(db.Float, nullable=False)

    term_id = db.Column(db.Integer, db.ForeignKey('google_term.id'), primary_key=True, nullable=False)
    term = db.relationship(
        'GoogleTerm',
        backref=db.backref('scores', lazy='dynamic', cascade='all,delete,delete-orphan'))

    def __repr__(self):
        return '<GoogleScore %s %f>' % (
            self.day.strftime('%Y-%m-%d'), self.value)


model_twitter_ngrams = db.Table(
    'model_twitter_ngrams',
    db.Column('model_id', db.Integer, db.ForeignKey('model.id'), nullable=False),
    db.Column('twitter_ngram_id', db.Integer, db.ForeignKey('twitter_ngram.id'), nullable=False)
)


class TwitterNgram(db.Model):
    """An NGram that a Twitter-type model might use, specific to a region"""
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    ngram = db.Column(db.Text, index=True, nullable=False)
    region = db.Column(db.Text, index=True, nullable=False)

    models = db.relationship(
        'Model',
        secondary=model_twitter_ngrams,
        backref=db.backref('twitter_ngrams', lazy='dynamic'))

    def __repr__(self):
        return '<TwitterNgram %s>' % self.ngram


class TwitterScore(db.Model):
    """The raw score from Twitter for a single NGram on a single day"""
    day = db.Column(db.Date, primary_key=True, nullable=False)
    value = db.Column(db.Float, nullable=False)

    ngram_id = db.Column(db.Integer, db.ForeignKey('twitter_ngram.id'), primary_key=True, nullable=False)
    ngram = db.relationship(
        'TwitterNgram',
        backref=db.backref('scores', lazy='dynamic', cascade='all,delete,delete-orphan'))

    def __repr__(self):
        return '<TwitterScore %s %f>' % (
            self.day.strftime('%Y-%m-%d'), self.value)


def init_app(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../data.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
