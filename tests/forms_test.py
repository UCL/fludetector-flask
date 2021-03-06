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
from fludetector.forms import GetScoresWebForm
from fludetector.models import db, Model, ModelScore, GoogleScore
from dateutil.relativedelta import relativedelta
import datetime
import unittest


class FormsTest(unittest.TestCase):

    @staticmethod
    def create_app():
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.app_context().push()
        return app

    def setUp(self):
        db.init_app(FormsTest.create_app())
        db.create_all()
        db.engine.execute('insert into model values (1, "Test Model", "google", 1, "matlab_function,1")')
        score = 35.5
        start_date = datetime.date.today() - datetime.timedelta(days=31)
        for i in xrange(32):
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

    def testGetScoresWebForm(self):
        model = db.session.query(Model).filter_by(public=True).first()
        score = model.last_score
        self.assertEqual(score.day, datetime.date.today())
        self.assertEqual(score.region, 'e')
        self.assertEqual(score.value, 4.5)
        scores_form = GetScoresWebForm(None, model_regions=[(score.model, score.region)])
        today = datetime.date.today()
        input_start = '<input id="start" name="start" type="text" value="{0}">'.format(today - relativedelta(months=1))
        input_end = '<input id="end" name="end" type="text" value="{0}">'.format(today)
        self.assertEqual(scores_form.end.__html__(), input_end)
        self.assertEqual(scores_form.start.__html__(), input_start)
        all_scores = scores_form.model_regions.data[0][0].scores.all()
        self.assertEqual(len(all_scores), 32)
