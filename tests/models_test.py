from flask import Flask
from fludetector.models import GoogleLog, Model, ModelScore, db
from sqlalchemy.exc import IntegrityError
import unittest
import datetime


class ModelsTest(unittest.TestCase):

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

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def testGoogleLog(self):
        """ Creates and persists a valid GoogleLog instance """
        gl = GoogleLog()
        gl.score_date = datetime.date.today()
        gl.score_timestamp = datetime.datetime.utcnow()
        expected = gl.__repr__()
        db.session.add(gl)
        db.session.commit()
        gls = GoogleLog.query.all()
        self.assertIn(gl, gls)
        self.assertEquals(str(gls[0]), expected)

    def testGoogleLogNullDate(self):
        """ Attempts to persist an invalid GoogleLog instance when score_date is None """
        gl = GoogleLog()
        gl.score_timestamp = datetime.datetime.utcnow()
        self.assertIsNone(gl.score_date)
        db.session.add(gl)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def testGoogleLogNullTimestamp(self):
        """ Attempts to persist an invalid GoogleLog instance when score_timestamp is None """
        gl = GoogleLog()
        gl.score_date = datetime.date.today()
        self.assertIsNone(gl.score_timestamp)
        db.session.add(gl)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def testModel(self):
        """ Evaluates methods not annotated as @property"""
        ml = Model()
        ml.name = 'Test Model'
        ml.type = 'google'
        ml.public = True
        ml.data = 'matlab_function,1'
        db.session.add(ml)
        score = 6.5
        day = datetime.date.today() - datetime.timedelta(days=3)
        for i in xrange(4):
            ms = ModelScore()
            ms.day = day + datetime.timedelta(days=i)
            ms.region = 'e'
            ms.value = score - i
            ms.model_id = 1
            db.session.add(ms)
        db.session.commit()
        dbmodel = db.session.query(Model).first()
        expected = db.session.query(ModelScore).all()
        result_get_scores = dbmodel.get_scores(start=day, end=datetime.date.today(), region='e', resolution=1)
        self.assertEqual(result_get_scores, expected)
        result_regions = dbmodel.scores_for('e').all()
        self.assertEqual(result_regions, expected)
        result_get_data = dbmodel.get_data()
        self.assertEqual(result_get_data['matlab_function'], 'matlab_function')
        self.assertEqual(result_get_data['average_window_size'], 1)


if __name__ == '__main__':
    unittest.main()
