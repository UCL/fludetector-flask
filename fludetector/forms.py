from datetime import timedelta

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import Form, DateField, SelectField, StringField, IntegerField, FieldList, ValidationError, BooleanField, TextAreaField
from wtforms.validators import InputRequired, DataRequired, NumberRange
from sqlalchemy.orm.exc import NoResultFound

from fludetector.models import db, Model, REGIONS, GoogleTerm, TwitterNgram


class ModelRegionField(StringField):

    def __init__(self, *args, **kwargs):
        kwargs['validators'] = [DataRequired()]
        super(ModelRegionField, self).__init__(*args, **kwargs)

    def process_data(self, model_region):
        self.data = model_region

    def process_formdata(self, valuelist):
        super(ModelRegionField, self).process_formdata(valuelist)
        model_id, region = self.data.split('-')
        self.data = (None, None)  # So that data is always a tuple, even if processing fails
        if region not in REGIONS:
            raise ValueError('No region with code %s' % region)
        model_id = int(model_id)
        model = Model.query.get(model_id)
        if not model:
            raise ValueError('No model with ID %d' % model_id)
        self.data = (model, region)

    def _value(self):
        if self.data:
            return '%d-%s' % (self.data[0].id, self.data[1])
        return ''


class TermsListField(TextAreaField):

    def process_data(self, terms):
        self.data = terms

    def process_formdata(self, valuelist):
        super(TermsListField, self).process_formdata(valuelist)
        terms_list = self.data.split('\n')
        self.data = []
        for term in terms_list:
            term = term.strip()
            if not term:
                continue
            try:
                t = GoogleTerm.query.filter_by(term=term).one()
            except NoResultFound:
                t = GoogleTerm()
                t.term = term
            self.data.append(t)

    def _value(self):
        if self.data:
            return '\n'.join(t.term for t in self.data)
        return ''


class NGramsListField(TextAreaField):

    def __init__(self, *args, **kwargs):
        self.region = kwargs.pop('region')
        super(NGramsListField, self).__init__(*args, **kwargs)

    def add_ngram(self, ngram):
        if not self.data:
            self.data = []
        self.data.append(ngram)

    def process_data(self, ngrams):
        self.data = ngrams

    def process_formdata(self, valuelist):
        super(NGramsListField, self).process_formdata(valuelist)
        ngrams_list = self.data.split('\n')
        self.data = []
        for ngram in ngrams_list:
            ngram = ngram.strip()
            if not ngram:
                continue
            try:
                n = TwitterNgram.query.filter_by(ngram=ngram, region=self.region).one()
            except NoResultFound:
                n = TwitterNgram()
                n.ngram = ngram
                n.region = self.region
            self.data.append(n)

    def _value(self):
        if self.data:
            return '\n'.join(t.ngram for t in self.data)
        return ''


class ModelField(IntegerField):

    def __init__(self, *args, **kwargs):
        kwargs['validators'] = [InputRequired()]
        super(ModelField, self).__init__(*args, **kwargs)

    def process_data(self, model):
        self.data = model

    def process_formdata(self, valuelist):
        super(ModelField, self).process_formdata(valuelist)
        id = self.data
        if id:
            self.data = Model.query.get(id)

    def _value(self):
        if self.data:
            return '%d' % self.data.id
        return ''


class RegionField(SelectField):

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = list(REGIONS.iteritems())
        kwargs['validators'] = [InputRequired()]
        super(RegionField, self).__init__(*args, **kwargs)


class GetScoresForm(Form):
    start = DateField('Start', validators=[DataRequired()])
    end = DateField('End', validators=[DataRequired()])
    resolution = SelectField(
        'Resolution',
        choices=[('day', 'Day'), ('week', 'Week')],
        default='day')
    smoothing = SelectField(
        'Smoothing',
        choices=[(0, 'No smoothing'), (3, '3-day moving average'), (5, '5-day moving average'), (7, '7-day moving average')],
        default=0,
        coerce=int)


class GetScoresWebForm(GetScoresForm):
    model_regions = FieldList(ModelRegionField('Model-Region'))

    def __init__(self, *args, **kwargs):
        super(GetScoresWebForm, self).__init__(*args, **kwargs)
        if self.model_regions.data and not self.start.data:
            start = self.model_regions.data[0][0].last_score.day
            start = start - timedelta(days=7)
            self.start.process_data(start)
        if self.start.data and not self.end.data:
            end = self.start.data + timedelta(days=14)
            self.end.process_data(end)

    def scores(self):
        if self.validate():
            return [
                (s, s.smoothed(self.smoothing.data))
                for (m, r) in self.model_regions.data
                for s in m.get_scores(self.start.data, self.end.data, r, self.resolution.data)]
        return []


class GetScoresApiForm(GetScoresForm):
    model = ModelField('Model')
    region = RegionField('Region')

    def __init__(self, *args, **kwargs):
        super(GetScoresApiForm, self).__init__(*args, **kwargs)
        if self.model.data and not self.start.data:
            start = self.model.data.last_score.day
            start = start - timedelta(days=7)
            self.start.process_data(start)
        if self.start.data and not self.end.data:
            end = self.start.data + timedelta(days=14)
            self.end.process_data(end)

    def scores(self):
        if self.validate():
            scores = self.model.data.get_scores(
                self.start.data, self.end.data, self.region.data, self.resolution.data)
            return [
                {'date': s.day.strftime('%Y-%m-%d'), 'score': s.smoothed(self.smoothing.data)}
                for s in scores]


class DeleteModelForm(FlaskForm):
    name = StringField(
        'Name',
        description='To confirm that you want to delete this model, please type its name',
        validators=[InputRequired()])

    def __init__(self, model, *args, **kwargs):
        super(DeleteModelForm, self).__init__(*args, **kwargs)
        self.model = model

    def validate_name(form, field):
        if field.data != form.model.name:
            raise ValidationError('Names do not match')


class CreateModelForm(FlaskForm):
    name = StringField(
        'Name',
        description='A human-readable name for the model',
        validators=[InputRequired()])
    type = SelectField(
        'Type',
        choices=[('google', 'google'), ('csv', 'csv'), ('twitter', 'twitter')])
    public = BooleanField(
        'Public?',
        description='This model should be available to the public (website and API)')

    @staticmethod
    def factory(type, model=None):
        if type == 'google':
            return CreateGoogleModelForm(obj=model, type=type)
        if type == 'twitter':
            return CreateTwitterModelForm(obj=model, type=type)
        return CreateModelForm(obj=model, type=type)


class CreateGoogleModelForm(CreateModelForm):
    matlab_function = StringField(
        'Matlab Function',
        description='The Matlab function to run over the raw Google data',
        default='infer_ILI_rate_google_v4',
        validators=[InputRequired()])
    average_window_size = IntegerField(
        'Average Window Size',
        description="Before passing data to Matlab, the points can be averaged over a number of days. How many days should this model average data over? 1 means no averaging, 2 means average today's and yesterday's scores, etc. etc.",
        default=1,
        validators=[InputRequired(), NumberRange(min=1)])
    google_terms = TermsListField(
        'Search Terms',
        description='A list of the search queries this model uses. Separated by newlines.',
        render_kw={'rows': 30})


class CreateTwitterModelForm(CreateModelForm):
    matlab_function = StringField(
        'Matlab Function',
        description='The Matlab function to run over Twitter n-gram counts',
        default='infer_ILI_rate_twitter_v3',
        validators=[InputRequired()])
    average_window_size = IntegerField(
        'Average Window Size',
        description="Before passing data to Matlab, the points can be averaged over a number of days. How many days should this model average data over? 1 means no averaging, 2 means average today's and yesterday's scores, etc. etc.",
        default=7,
        validators=[InputRequired(), NumberRange(min=1)])
    ngrams_e = NGramsListField(
        'N-Grams for England',
        region='e',
        description='What are the n-grams of interest for the whole England region',
        render_kw={'rows': 15})
    ngrams_l = NGramsListField(
        'N-Grams for London',
        region='l',
        description='What are the n-grams of interest for the London region',
        render_kw={'rows': 15})
    ngrams_m = NGramsListField(
        'N-Grams for the Midlands',
        region='m',
        description='What are the n-grams of interest for the Midlands region',
        render_kw={'rows': 15})
    ngrams_n = NGramsListField(
        'N-Grams for North England',
        region='n',
        description='What are the n-grams of interest for the North England region',
        render_kw={'rows': 15})
    ngrams_s = NGramsListField(
        'N-Grams for South England',
        region='s',
        description='What are the n-grams of interest for the South England region',
        render_kw={'rows': 15})

    def populate_obj(self, obj):
        super(CreateTwitterModelForm, self).populate_obj(obj)
        for ngrams in [self.ngrams_e, self.ngrams_l, self.ngrams_m, self.ngrams_n, self.ngrams_s]:
            for ngram in ngrams.data:
                obj.twitter_ngrams.append(ngram)

    def __init__(self, *args, **kwargs):
        super(CreateTwitterModelForm, self).__init__(*args, **kwargs)
        ngrams = []
        if 'obj' in kwargs and kwargs['obj']:
            ngrams = kwargs['obj'].twitter_ngrams
        if 'twitter_ngrams' in kwargs:
            ngrams = kwargs['twitter_ngrams']
        for ngram in ngrams:
            {
                'e': self.ngrams_e,
                'l': self.ngrams_l,
                'm': self.ngrams_m,
                'n': self.ngrams_n,
                's': self.ngrams_s
            }.get(ngram.region).add_ngram(ngram)


class RunModelForm(FlaskForm):
    start = DateField(
        'Start',
        description='Analyse data from this date onwards',
        validators=[DataRequired()])
    end = DateField(
        'End',
        description='Analyse data up to (not including) this date',
        validators=[DataRequired()])

    @staticmethod
    def factory(model):
        if model.type == 'csv':
            return RunCsvModelForm()
        return RunModelForm()

    def to_dict(self):
        return {
            'start': self.start.data,
            'end': self.end.data
        }


class RunCsvModelForm(RunModelForm):
    csv_file = FileField(
        'CSV File',
        description='The file to read data from',
        validators=[FileRequired()])

    def to_dict(self):
        d = super(RunCsvModelForm, self).to_dict()
        path = '/tmp/fludetector_uploaded.csv'
        self.csv_file.data.save(path)
        d['csv'] = path
        return d


class ExportModelForm(FlaskForm):
    start = DateField(
        'Start',
        description='Export data from this date onwards',
        validators=[DataRequired()])
    end = DateField(
        'End',
        description='Export data up to (not including) this date',
        validators=[DataRequired()])
