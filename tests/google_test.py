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
from flask import Flask
from fludetector.models import db, Model, ModelScore, GoogleScore
from fludetector.sources import google
import datetime
import unittest


class GoogleTest(unittest.TestCase):

    @staticmethod
    def create_app():
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.app_context().push()
        return app

    def setUp(self):
        db.init_app(GoogleTest.create_app())
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

