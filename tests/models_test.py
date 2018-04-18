from flask import Flask
from fludetector.models import GoogleLog, db
from sqlalchemy.exc import IntegrityError
import unittest
import datetime
import os


class ModelsTest(unittest.TestCase):

    def setUp(self):
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        app.app_context().push()
        db.session.close()
        db.drop_all()
        db.create_all()

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

    def tearDown(self):
        db.drop_all()
        db.engine.dispose()
        os.remove('../test.db')


if __name__ == '__main__':
    unittest.main()
