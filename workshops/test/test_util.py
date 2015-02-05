# coding: utf-8
import cgi
from datetime import datetime
from io import StringIO
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.serializers import JSONSerializer
from django.test import TestCase
from django.core.urlresolvers import reverse

from ..models import Site, Event, Role, Person
from ..util import upload_person_task_csv, verify_upload_person_task

from .base import TestBase

class UploadPersonTaskCSVTestCase(TestCase):

    def compute_from_string(self, csv_str):
        ''' wrap up buffering the raw string & parsing '''
        csv_buf = StringIO(csv_str)
        # compute & return
        return upload_person_task_csv(csv_buf)

    def test_basic_parsing(self):
        ''' See Person.PERSON_UPLOAD_FIELDS for field ordering '''
        csv = """personal,middle,family,email
john,a,doe,johndoe@email.com
jane,a,doe,janedoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)

        # assert
        self.assertEqual(len(person_tasks), 2)

        person = person_tasks[0]
        self.assertSetEqual(set(('person', 'role', 'event', 'errors')), set(person.keys()))

        person_dict = person['person']
        self.assertSetEqual(set(Person.PERSON_UPLOAD_FIELDS), set(person_dict.keys()))

    def test_csv_without_required_field(self):
        ''' All fields in Person.PERSON_UPLOAD_FIELDS must be in csv '''
        bad_csv = """personal,middle,family
john,,doe"""
        person_tasks, empty_fields = self.compute_from_string(bad_csv)
        self.assertTrue('email' in empty_fields)

    def test_csv_with_mislabeled_field(self):
        ''' It pays to be strict '''
        bad_csv = """personal,middle,family,emailaddress
john,m,doe,john@doe.com"""
        person_tasks, empty_fields = self.compute_from_string(bad_csv)
        self.assertTrue('email' in empty_fields)

    def test_empty_field(self):
        ''' Ensure we don't mis-order fields given blank data '''
        csv = """personal,middle,family,email
john,,doe,johndoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)
        person = person_tasks[0]
        self.assertEqual(person['person']['middle'], '')

    def test_serializability_of_parsed(self):
        csv = """personal,middle,family,email
john,a,doe,johndoe@email.com
jane,a,doe,janedoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)

        try:
            serializer = JSONSerializer()
            serializer.dumps(person_tasks)
        except TypeError:
            self.fail('Dumping person_tasks to JSON unexpectedly failed!')


class CSVBulkUploadTestBase(TestBase):
    """
    Simply provide necessary setUp and make_data functions that are used in two
    different TestCases
    """
    def setUp(self):
        super(CSVBulkUploadTestBase, self).setUp()
        test_site = Site.objects.create(domain='example.com',
                                        fullname='Test Site')

        Role.objects.create(name='Instructor')
        Event.objects.create(start=datetime.now(),
                             site=test_site,
                             slug='foobar',
                             admin_fee=100)

    def make_csv_data(self):
        """
        Sample CSV data
        """
        return """personal,middle,family,email,event,role
John,S,Doe,notin@db.com,foobar,Instructor
"""

    def make_data(self):
        csv_str = self.make_csv_data()
        # upload_person_task_csv gets thoroughly tested in
        # UploadPersonTaskCSVTestCase
        data, _ = upload_person_task_csv(StringIO(csv_str))
        return data


class VerifyUploadPersonTask(CSVBulkUploadTestBase):
    ''' Scenarios to test:
        - Everything is good
        - no 'person' key
        - event DNE
        - role DNE
        - email already exists
    '''

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


class BulkUploadUsersViewTestCase(CSVBulkUploadTestBase):
    def test_event_name_dropped(self):
        """
        Test for regression:
        test whether event name is really getting empty when user changes it
        from "foobar" to empty.
        """
        data = self.make_data()

        # dirty: instead of upload a file simply save the data to the session
        # because "self.client" is anonymous user, there are some implications,
        # for example Django session is not available… See:
        #   https://code.djangoproject.com/ticket/10899
        # The solution is taken from:
        #   http://stackoverflow.com/a/25151753
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store['bulk-add-people'] = data
        store.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

        # send exactly what's in 'data', except for the 'event' field: leave
        # this one empty
        payload = {
            "personal": data[0]['person']['personal'],
            "middle": data[0]['person']['middle'],
            "family": data[0]['person']['family'],
            "email": data[0]['person']['email'],
            "event": "",
            "role": "",
            "verify": "Verify",
        }
        rv = self.client.post(reverse('person_bulk_add_confirmation'), payload)
        self.assertEqual(rv.status_code, 200)
        _, params = cgi.parse_header(rv['content-type'])
        charset = params['charset']
        content = rv.content.decode(charset)
        self.assertNotIn('foobar', content)
