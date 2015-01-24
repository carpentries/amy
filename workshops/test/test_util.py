# this probably needs refactored for py3
from datetime import datetime
from StringIO import StringIO

from django.test import TestCase

from ..models import Site, Event, Role, Person
from ..util import PERSON_UPLOAD_FIELDS, upload_person_task_csv,\
    verify_upload_person_task

from .base import TestBase

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


class VerifyUploadPersonTask(TestBase):
    ''' Scenarios to test:
        - Everything is good
        - no 'person' key
        - event DNE
        - role DNE
        - email already exists
    '''
    def setUp(self):
        super(VerifyUploadPersonTask, self).setUp()
        test_site = Site.objects.create(domain='example.com',
            fullname='Test Site')

        Role.objects.create(name='Instructor')
        Event.objects.create(start=datetime.now(),
                             site=test_site,
                             slug='foobar',
                             admin_fee=100)

    def make_data(self):
        # this data structure mimics what we get from upload_person_task_csv
        return [{
            'person': {
                'personal': 'John',
                'middle': 'S',
                'family': 'Doe',
                'email': 'notin@db.com',
            },
            'role': 'Instructor',
            'event': 'foobar',
            'errors': None,
        }]

    def test_verify_with_good_data(self):
        good_data = self.make_data()
        has_errors = verify_upload_person_task(good_data)
        self.assertFalse(has_errors)
        # make sure 'errors' wasn't set
        self.assertIsNone(good_data[0]['errors'])

    def test_verify_data_has_no_person_key(self):
        bad_data = self.make_data()
        del bad_data[0]['person']
        has_errors = verify_upload_person_task(bad_data)
        self.assertTrue(has_errors)

        errors = bad_data[0]['errors']
        # 1 error, 'person' in it
        self.assertTrue(len(errors) == 1)
        self.assertTrue('person' in errors[0])

    def test_verify_event_dne(self):
        bad_data = self.make_data()
        bad_data[0]['event'] = 'dne'
        has_errors = verify_upload_person_task(bad_data)
        self.assertTrue(has_errors)

        errors = bad_data[0]['errors']
        self.assertTrue(len(errors) == 1)
        self.assertTrue('Event with slug' in errors[0])

    def test_very_role_dne(self):
        bad_data = self.make_data()
        bad_data[0]['role'] = 'foobar'

        has_errors = verify_upload_person_task(bad_data)
        self.assertTrue(has_errors)

        errors = bad_data[0]['errors']
        self.assertTrue(len(errors) == 1)
        self.assertTrue('Role with name' in errors[0])

    def test_verify_email_exists(self):
        bad_data = self.make_data()
        # test both matching and case-insensitive matching
        for email in ('harry@hogwarts.edu', 'HARRY@hogwarts.edu'):
            bad_data[0]['person']['email'] = 'harry@hogwarts.edu'

            has_errors = verify_upload_person_task(bad_data)
            self.assertTrue(has_errors)

            errors = bad_data[0]['errors']
            self.assertTrue(len(errors) == 1)
            self.assertTrue('User with email' in errors[0])
