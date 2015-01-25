# this probably needs refactored for py3
from StringIO import StringIO

from django.test import TestCase

from .util import PERSON_UPLOAD_FIELDS, upload_person_task_csv


class UploadPersonTaskCSVTestCase(TestCase):

    def compute_from_string(self, csv_str):
        ''' wrap up buffering the raw string & parsing '''
        csv_buf = StringIO(csv_str)
        # compute & return
        return upload_person_task_csv(csv_buf)

    def test_basic_parsing(self):
        ''' See views.PERSON_UPLOAD_FIELDS for field ordering '''
        csv = """personal,middle,family,email\njohn,a,doe,johndoe@email.com\n,jane,a,doe,janedoe@email.com"""
        person_tasks = self.compute_from_string(csv)

        # assert
        self.assertEqual(len(person_tasks), 2)

        person = person_tasks[0]
        for key in ('person', 'role', 'event', 'errors'):
            self.assertIn(key, person)

        person_dict = person['person']
        for key in PERSON_UPLOAD_FIELDS:
            self.assertIn(key, person_dict)

    def test_empty_field(self):
        ''' Ensure we don't mis-order fields given blank data '''
        csv = """personal,middle,family,email\njohn,,doe,johndoe@email.com"""
        person = self.compute_from_string(csv)[0]

        self.assertEqual(person['person']['middle'], '')
