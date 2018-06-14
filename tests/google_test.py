from flask import Flask
from fludetector.models import db, Model, ModelScore, GoogleScore
from fludetector.sources import google
import datetime
import unittest


class GoogleTest(unittest.TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.app_context().push()
        return app

    def setUp(self):
        db.init_app(self.create_app())
        db.create_all()
        db.engine.execute('insert into model values (1, "Test Model", "google", 1, "matlab_function,1")')
        score = 6.5
        start_date = datetime.date.today() - datetime.timedelta(days=5)
        for i in xrange(4):
            ms = ModelScore()
            ms.day = start_date + datetime.timedelta(days=i)
            ms.region = 'e'
            ms.value = score - i
            ms.model_id = 1
            db.session.add(ms)
            gs = GoogleScore()
            gs.day = start_date + datetime.timedelta(days=i)
            gs.value = score - i
            gs.term_id = 1
            db.session.add(gs)
        db.session.commit()
        db.engine.execute('insert into google_term values (1, "Term 1")')
        db.engine.execute('insert into model_google_terms values (1, 1)')

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def testDaysMissingGoogleScore(self):
        """ Expect 2 dates missing: today and yesterday """
        model = db.session.query(Model).first()
        start_date = datetime.date.today() - datetime.timedelta(days=3)
        end_date = datetime.date.today()
        google_missing = list(google.days_missing_google_score(model, start_date, end_date))
        self.assertEqual(min(google_missing), datetime.date.today() - datetime.timedelta(days=1))
        self.assertEqual(max(google_missing), datetime.date.today())

    def testDaysMissingModelScore(self):
        """ Expect 2 dates missing: today and yesterday """
        model = db.session.query(Model).first()
        start_date = datetime.date.today() - datetime.timedelta(days=3)
        end_date = datetime.date.today()
        model_missing = list(google.days_missing_model_score(model, start_date, end_date))
        self.assertEqual(min(model_missing), datetime.date.today() - datetime.timedelta(days=1))
        self.assertEqual(max(model_missing), datetime.date.today())

    def testBatches(self):
        """ Expect one batch (batches of up to 30 terms) """
        model = db.session.query(Model).first()
        start_date = datetime.date.today() - datetime.timedelta(days=1)
        end_date = datetime.date.today()
        test_batch = google.batches(model, start_date, end_date)
        b = next(test_batch) # only one element expected
        self.assertEqual(b[0][0].term, 'Term 1')
        self.assertEqual(b[1], start_date)
        self.assertEqual(b[2], end_date)

