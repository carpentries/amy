# coding: utf-8
import cgi
from datetime import datetime
from io import StringIO
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.serializers import JSONSerializer
from django.test import TestCase
from django.core.urlresolvers import reverse

from ..models import Site, Event, Role, Person, Task
from ..util import upload_person_task_csv, verify_upload_person_task

from .base import TestBase


class UploadPersonTaskCSVTestCase(TestCase):

    def compute_from_string(self, csv_str):
        ''' wrap up buffering the raw string & parsing '''
        csv_buf = StringIO(csv_str)
        # compute and return
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
        self.assertTrue(
            set(person.keys()).issuperset(set(Person.PERSON_UPLOAD_FIELDS)))

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
        self.assertEqual(person['middle'], '')

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

    def test_no_new_column_added(self):
        '''
        Ensure more number of fields are not added by increasing
        the number of columns
        '''
        csv = """personal,middle,family,email,event,role,phone_no
john,a,doe,johndoe@email.com,2015-09-01-ttt-online,learner,9991239011
jane,a,doe,janedoe@email.com,2015-09-01-ttt-online,learner,9991239021"""
        person_tasks, _ = self.compute_from_string(csv)
        person = person_tasks[0]
        self.assertTrue('phone_no' not in person)

    def test_number_of_columns(self):
        '''
        Ensure number of columns remains same in case of
        empty fields or extra fields
        '''

        csv = """personal,middle,family,email,event,role,phone_no
john,a,doe,johndoe@email.com,2015-09-01-ttt-online,learner,9991239011"""
        person_tasks, _ = self.compute_from_string(csv)
        person = person_tasks[0]
        fields = list(Person.PERSON_TASK_UPLOAD_FIELDS)
        fields.append('errors')
        self.assertEqual(
            sorted(
                person.keys(), key=str.lower), sorted(
                fields, key=str.lower))

        csv = """personal,middle,family,email,role
john,a,doe,johndoe@email.com,learner"""
        person_tasks, _ = self.compute_from_string(csv)
        person = person_tasks[0]
        fields = list(Person.PERSON_TASK_UPLOAD_FIELDS)
        fields.append('errors')
        self.assertEqual(
            sorted(
                person.keys(), key=str.lower), sorted(
                fields, key=str.lower))
        self.assertEqual(person['event'], None)

        csv = """personal,middle,family,email
john,a,doe,johndoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)
        person = person_tasks[0]
        fields = list(Person.PERSON_TASK_UPLOAD_FIELDS)
        fields.append('errors')
        self.assertEqual(
            sorted(
                person.keys(), key=str.lower), sorted(
                fields, key=str.lower))
        self.assertEqual(person['event'], None)
        self.assertEqual(person['role'], None)

        csv = """personal,family,email
john,,doe,johndoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)
        person = person_tasks[0]
        fields = list(Person.PERSON_TASK_UPLOAD_FIELDS)
        fields.append('errors')
        self.assertEqual(
            sorted(
                person.keys(), key=str.lower), sorted(
                fields, key=str.lower))


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

        self._setUpUsersAndLogin()

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

    def test_verify_event_doesnt_exist(self):
        bad_data = self.make_data()
        bad_data[0]['event'] = 'no-such-event'
        has_errors = verify_upload_person_task(bad_data)
        self.assertTrue(has_errors)

        errors = bad_data[0]['errors']
        self.assertTrue(len(errors) == 1)
        self.assertTrue('Event with slug' in errors[0])

    def test_verify_role_doesnt_exist(self):
        bad_data = self.make_data()
        bad_data[0]['role'] = 'foobar'

        has_errors = verify_upload_person_task(bad_data)
        self.assertTrue(has_errors)

        errors = bad_data[0]['errors']
        self.assertTrue(len(errors) == 1)
        self.assertTrue('Role with name' in errors[0])

    def test_verify_email_caseinsensitive_matches(self):
        bad_data = self.make_data()
        # test both matching and case-insensitive matching
        for email in ('harry@hogwarts.edu', 'HARRY@hogwarts.edu'):
            bad_data[0]['email'] = email
            bad_data[0]['personal'] = 'Harry'
            bad_data[0]['middle'] = None
            bad_data[0]['family'] = 'Potter'

            has_errors = verify_upload_person_task(bad_data)
            self.assertFalse(has_errors)

    def test_verify_name_matching_existing_user(self):
        bad_data = self.make_data()
        bad_data[0]['email'] = 'harry@hogwarts.edu'
        has_errors = verify_upload_person_task(bad_data)
        self.assertTrue(has_errors)
        errors = bad_data[0]['errors']
        self.assertEqual(len(errors), 1)
        self.assertTrue("Personal, middle or family name of existing user"
                        " don't match" in errors[0])

    def test_verify_existing_user_has_workshop_role_provided(self):
        bad_data = [
            {
                'email': 'harry@hogwarts.edu',
                'personal': 'Harry',
                'middle': None,
                'family': 'Potter',
                'event': '',
                'role': '',
            }
        ]
        has_errors = verify_upload_person_task(bad_data)
        self.assertTrue(has_errors)
        errors = bad_data[0]['errors']
        self.assertEqual(len(errors), 1)
        self.assertTrue("User exists but no event and role to assign"
                        in errors[0])


class BulkUploadUsersViewTestCase(CSVBulkUploadTestBase):

    def setUp(self):
        super().setUp()
        Role.objects.create(name='Helper')

    def test_event_name_dropped(self):
        """
        Test for regression:
        test whether event name is really getting empty when user changes it
        from "foobar" to empty.
        """
        data = self.make_data()

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store['bulk-add-people'] = data
        store.save()

        # send exactly what's in 'data', except for the 'event' field: leave
        # this one empty
        payload = {
            "personal": data[0]['personal'],
            "middle": data[0]['middle'],
            "family": data[0]['family'],
            "email": data[0]['email'],
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

    def test_upload_existing_user(self):
        """
        Check if uploading existing users ends up with them having new role
        assigned.

        This is a special case of upload feature: if user uploads a person that
        already exists we should only assign new role and event to that person.
        """
        csv = """personal,middle,family,email,event,role
Harry,,Potter,harry@hogwarts.edu,foobar,Helper
"""
        data, _ = upload_person_task_csv(StringIO(csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store['bulk-add-people'] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": data[0]['personal'],
            "middle": data[0]['middle'],
            "family": data[0]['family'],
            "email": data[0]['email'],
            "event": data[0]['event'],
            "role": data[0]['role'],
            "confirm": "Confirm",
        }

        people_pre = set(Person.objects.all())
        tasks_pre = set(Task.objects.filter(person=self.harry,
                                            event__slug="foobar"))

        rv = self.client.post(reverse('person_bulk_add_confirmation'), payload,
                              follow=True)
        self.assertEqual(rv.status_code, 200)

        people_post = set(Person.objects.all())
        tasks_post = set(Task.objects.filter(person=self.harry,
                                             event__slug="foobar"))

        # make sure no-one new was added
        self.assertSetEqual(people_pre, people_post)

        # make sure that Harry was assigned a new role
        self.assertNotEqual(tasks_pre, tasks_post)

    def test_upload_existing_user_existing_task(self):
        """
        Check if uploading existing user and assigning existing task to that
        user fails.
        """
        foobar = Event.objects.get(slug="foobar")
        instructor = Role.objects.get(name="Instructor")
        Task.objects.create(person=self.harry, event=foobar, role=instructor)

        csv = """personal,middle,family,email,event,role
Harry,,Potter,harry@hogwarts.edu,foobar,Instructor
"""
        data, _ = upload_person_task_csv(StringIO(csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store['bulk-add-people'] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": data[0]['personal'],
            "middle": data[0]['middle'],
            "family": data[0]['family'],
            "email": data[0]['email'],
            "event": data[0]['event'],
            "role": data[0]['role'],
            "confirm": "Confirm",
        }

        tasks_pre = set(Task.objects.filter(person=self.harry,
                                            event__slug="foobar"))
        rv = self.client.post(reverse('person_bulk_add_confirmation'), payload,
                              follow=True)
        tasks_post = set(Task.objects.filter(person=self.harry,
                                             event__slug="foobar"))
        self.assertEqual(tasks_pre, tasks_post)
        self.assertEqual(rv.status_code, 400)

        # we need to decode rv.content, because it's bytes, not str
        _, params = cgi.parse_header(rv['content-type'])
        charset = params['charset']
        content = rv.content.decode(charset)
        self.assertIn('already has role', content)

    def test_upload_existing_user_new_task_casesensitive_email(self):
        """
        Check if uploading existing user(case sensitive email) with a new task
        does not create a new user.
        """
        foobar = Event.objects.get(slug="foobar")
        instructor = Role.objects.get(name="Instructor")
        Task.objects.create(person=self.harry, event=foobar, role=instructor)

        test_site = Site.objects.get(fullname='Test Site')
        Event.objects.create(start=datetime.now(),
                             site=test_site,
                             slug='newbar',
                             admin_fee=200)

        csv = """personal,middle,family,email,event,role
Harry,,Potter,harry@hogwarts.edu,newbar,Instructor
"""
        data, _ = upload_person_task_csv(StringIO(csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store['bulk-add-people'] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": data[0]['personal'],
            "middle": data[0]['middle'],
            "family": data[0]['family'],
            "email": data[0]['email'],
            "event": data[0]['event'],
            "role": data[0]['role'],
            "confirm": "Confirm",
        }

        people_pre = set(Person.objects.all())
        tasks_pre = set(
            Task.objects.filter(
                person=self.harry,
                role__name="Instructor"))

        rv = self.client.post(reverse('person_bulk_add_confirmation'), payload,
                              follow=True)

        tasks_post = set(Task.objects.filter(person=self.harry,
                                             role__name="Instructor"))
        people_post = set(Person.objects.all())

        self.assertEqual(rv.status_code, 200)

        # make sure no new people added
        self.assertEqual(people_pre, people_post)
        # make sure a new task is added
        self.assertNotEqual(tasks_pre, tasks_post)

    def test_upload_existing_user_new_task_case_insensitive_email(self):
        """
        Check if uploading existing user(case insensitive email) with a new
        task does not create a new user.
        """

        foobar = Event.objects.get(slug="foobar")
        instructor = Role.objects.get(name="Instructor")
        Task.objects.create(person=self.harry, event=foobar, role=instructor)

        test_site = Site.objects.get(fullname='Test Site')
        Event.objects.create(start=datetime.now(),
                             site=test_site,
                             slug='newbar',
                             admin_fee=200)

        csv = """personal,middle,family,email,event,role
Harry,,Potter,Harry@hogwarts.edu,newbar,Instructor
"""
        data, _ = upload_person_task_csv(StringIO(csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store['bulk-add-people'] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": data[0]['personal'],
            "middle": data[0]['middle'],
            "family": data[0]['family'],
            "email": data[0]['email'],
            "event": data[0]['event'],
            "role": data[0]['role'],
            "confirm": "Confirm",
        }

        people_pre = set(Person.objects.all())
        tasks_pre = set(
            Task.objects.filter(
                person=self.harry,
                role__name="Instructor"))

        rv = self.client.post(reverse('person_bulk_add_confirmation'), payload,
                              follow=True)

        tasks_post = set(Task.objects.filter(person=self.harry,
                                             role__name="Instructor"))
        people_post = set(Person.objects.all())

        self.assertEqual(rv.status_code, 200)

        # make sure no new people added
        self.assertEqual(people_pre, people_post)
        # make sure a new task is added
        self.assertNotEqual(tasks_pre, tasks_post)
