# coding: utf-8
import cgi
from datetime import date, timedelta
from io import StringIO

from django.contrib.sessions.serializers import JSONSerializer
from django.urls import reverse

from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin
from workshops.models import Event, Organization, Person, Role, Tag, Task
from workshops.tests.base import TestBase
from workshops.util import upload_person_task_csv, verify_upload_person_task
import workshops.views


class UploadPersonTaskCSVTestCase(TestBase):
    def compute_from_string(self, csv_str):
        """ wrap up buffering the raw string & parsing """
        csv_buf = StringIO(csv_str)
        # compute and return
        return upload_person_task_csv(csv_buf)

    def test_basic_parsing(self):
        """ See Person.PERSON_UPLOAD_FIELDS for field ordering """
        csv = """personal,family,email
john,doe,johndoe@email.com
jane,doe,janedoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)

        # assert
        self.assertEqual(len(person_tasks), 2)

        person = person_tasks[0]
        self.assertTrue(set(person.keys()).issuperset(set(Person.PERSON_UPLOAD_FIELDS)))

    def test_csv_without_required_field(self):
        """ All fields in Person.PERSON_UPLOAD_FIELDS must be in csv """
        bad_csv = """personal,family
john,doe"""
        person_tasks, empty_fields = self.compute_from_string(bad_csv)
        self.assertTrue("email" in empty_fields)

    def test_csv_with_mislabeled_field(self):
        """ It pays to be strict """
        bad_csv = """personal,family,emailaddress
john,doe,john@doe.com"""
        person_tasks, empty_fields = self.compute_from_string(bad_csv)
        self.assertTrue("email" in empty_fields)

    def test_csv_with_empty_lines(self):
        csv = """personal,family,emailaddress
john,doe,john@doe.com
,,"""
        person_tasks, empty_fields = self.compute_from_string(csv)
        self.assertEqual(len(person_tasks), 1)
        person = person_tasks[0]
        self.assertEqual(person["personal"], "john")

    def test_empty_field(self):
        """ Ensure we don't mis-order fields given blank data """
        csv = """personal,family,email
john,,johndoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)
        person = person_tasks[0]
        self.assertEqual(person["family"], "")

    def test_serializability_of_parsed(self):
        csv = """personal,family,email
john,doe,johndoe@email.com
jane,doe,janedoe@email.com"""
        person_tasks, _ = self.compute_from_string(csv)

        try:
            serializer = JSONSerializer()
            serializer.dumps(person_tasks)
        except TypeError:
            self.fail("Dumping person_tasks to JSON unexpectedly failed!")

    def test_malformed_CSV_with_proper_header_row(self):
        csv = """personal,family,email
This is a malformed CSV
        """
        person_tasks, empty_fields = self.compute_from_string(csv)
        self.assertEqual(person_tasks[0]["personal"], "This is a malformed CSV")
        self.assertEqual(set(empty_fields), set(["family", "email"]))


class CSVBulkUploadTestBase(TestBase):
    """
    Simply provide necessary setUp and make_data functions that are used in two
    different TestCases
    """

    def setUp(self):
        super(CSVBulkUploadTestBase, self).setUp()
        test_host = Organization.objects.create(
            domain="example.com", fullname="Test Organization"
        )

        Role.objects.create(name="instructor")
        Role.objects.create(name="learner")
        Event.objects.create(start=date.today(), host=test_host, slug="foobar")

        self._setUpUsersAndLogin()

    def make_csv_data(self):
        """
        Sample CSV data
        """
        return """personal,family,email,event,role
John,Doe,notin@db.com,foobar,instructor
"""

    def make_data(self):
        csv_str = self.make_csv_data()
        # upload_person_task_csv gets thoroughly tested in
        # UploadPersonTaskCSVTestCase
        data, _ = upload_person_task_csv(StringIO(csv_str))
        return data


class VerifyUploadPersonTask(CSVBulkUploadTestBase):

    """Scenarios to test:
    - Everything is good
    - no 'person' key
    - event DNE
    - role DNE
    - email already exists
    """

    def test_verify_with_good_data(self):
        good_data = self.make_data()
        has_errors = verify_upload_person_task(good_data, match=True)
        self.assertFalse(has_errors)
        # make sure 'errors' wasn't set
        # 'errors' may be an empty list, which evaluates to False
        self.assertFalse(good_data[0]["errors"])

    def test_verify_event_doesnt_exist(self):
        bad_data = self.make_data()
        bad_data[0]["event"] = "no-such-event"
        has_errors = verify_upload_person_task(bad_data, match=True)
        self.assertTrue(has_errors)

        errors = bad_data[0]["errors"]
        self.assertEqual(len(errors), 1)
        self.assertTrue("Event with slug" in errors[0])

    def test_verify_role_doesnt_exist(self):
        bad_data = self.make_data()
        bad_data[0]["role"] = "foobar"

        has_errors = verify_upload_person_task(bad_data, match=True)
        self.assertTrue(has_errors)

        errors = bad_data[0]["errors"]
        self.assertTrue(len(errors) == 1)
        self.assertTrue("Role with name" in errors[0])

    def test_verify_email_caseinsensitive_matches(self):
        bad_data = self.make_data()
        # test both matching and case-insensitive matching
        for email in ("harry@hogwarts.edu", "HARRY@hogwarts.edu"):
            bad_data[0]["email"] = email
            bad_data[0]["personal"] = "Harry"
            bad_data[0]["family"] = "Potter"

            has_errors = verify_upload_person_task(bad_data, match=True)
            self.assertFalse(has_errors, "Bad email: {}".format(email))

    def test_email_missing(self):
        """This tests against regression in:
        https://github.com/swcarpentry/amy/issues/1394

        The issue: entries without emails (email=None) were caught in
        `Person.objects.get(email=email)`, which returned multiple objects
        (because we have many users with empty emails, and it doesn't violate
        UNIQUE constraint."""

        # make existing users loose their emails
        usernames = ["potter_harry", "granger_hermione", "weasley_ron"]
        Person.objects.filter(username__in=usernames).update(email=None)

        bad_data = [
            {
                "email": None,
                "personal": "Harry",
                "family": "Potter",
                "event": "foobar",
                "role": "learner",
            },
            {
                "email": None,
                "personal": "Hermione",
                "family": "Granger",
                "event": "foobar",
                "role": "learner",
            },
            {
                "email": None,
                "personal": "Ron",
                "family": "Weasley",
                "event": "foobar",
                "role": "learner",
            },
        ]
        # test for first occurrence of the error
        has_errors = verify_upload_person_task(bad_data, match=True)
        self.assertFalse(has_errors)
        # test for second occurrence of the error
        has_errors = verify_upload_person_task(bad_data, match=False)
        self.assertFalse(has_errors)

    def test_verify_existing_user_has_workshop_role_provided(self):
        bad_data = [
            {
                "email": "harry@hogwarts.edu",
                "personal": "Harry",
                "family": "Potter",
                "event": "",
                "role": "",
            }
        ]
        has_errors = verify_upload_person_task(bad_data, match=True)
        self.assertTrue(has_errors)
        errors = bad_data[0]["errors"]
        self.assertEqual(len(errors), 2)
        self.assertIn("Must have a role", errors[0])
        self.assertIn("Must have an event", errors[1])

    def test_username_from_existing_person(self):
        """Make sure the username is being changed for correct one."""
        data = [
            {
                "personal": "Harry",
                "family": "Potter",
                "username": "wrong_username",
                "email": "harry@hogwarts.edu",
                "event": "",
                "role": "",
                "existing_person_id": Person.objects.get(email="harry@hogwarts.edu").pk,
            }
        ]
        verify_upload_person_task(data)
        self.assertEqual("potter_harry", data[0]["username"])

    def test_username_from_nonexisting_person(self):
        """Make sure the username is not being changed."""
        data = [
            {
                "personal": "Harry",
                "family": "Frotter",
                "username": "supplied_username",
                "email": "h.frotter@hogwarts.edu",
                "event": "",
                "role": "",
                "existing_person_id": None,
            }
        ]
        verify_upload_person_task(data)
        self.assertEqual("supplied_username", data[0]["username"])

    def test_matched_similar_persons(self):
        """Ensure function finds matching persons."""
        data = [
            {
                "personal": "Harry",
                "family": "Potter",
                "username": "supplied_username",
                "email": "h.frotter@hogwarts.edu",
                "event": "",
                "role": "",
            },
            {
                "personal": "Romuald",
                "family": "Weazel",
                "username": "",
                "email": "rweasley@ministry.gov.uk",
                "event": "",
                "role": "",
            },
        ]
        verify_upload_person_task(data)

        self.assertEqual(len(data[0]["similar_persons"]), 1)
        self.assertEqual(len(data[1]["similar_persons"]), 1)

        self.assertEqual(data[0]["similar_persons"][0][0], self.harry.pk)
        self.assertEqual(data[1]["similar_persons"][0][0], self.ron.pk)

    def test_duplicate_errors(self):
        """Ensure errors about duplicate person in the database are present."""
        data = self.make_data()
        data[0]["personal"] = "Harry"
        data[0]["family"] = "Potter"
        data[0]["email"] = "harry@hogwarts.edu"
        verify_upload_person_task(data)
        self.assertEqual(len(data[0]["errors"]), 2)
        self.assertIn(
            "Person with this email address already exists.", data[0]["errors"]
        )
        self.assertIn("Person with this username already exists.", data[0]["errors"])


class BulkUploadUsersViewTestCase(CSVBulkUploadTestBase):
    def setUp(self):
        super().setUp()
        Role.objects.create(name="Helper")

    def test_event_name_dropped(self):
        """
        Test for regression:
        test whether event name is really getting empty when user changes it
        from "foobar" to empty.
        """
        data = self.make_data()

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        # send exactly what's in 'data', except for the 'event' field: leave
        # this one empty
        payload = {
            "personal": data[0]["personal"],
            "family": data[0]["family"],
            "username": data[0]["username"],
            "email": data[0]["email"],
            "event": "",
            "role": "",
            "verify": "Verify",
        }
        rv = self.client.post(reverse("person_bulk_add_confirmation"), payload)
        self.assertEqual(rv.status_code, 200)
        _, params = cgi.parse_header(rv["content-type"])
        charset = params["charset"]
        content = rv.content.decode(charset)
        self.assertNotIn("foobar", content)

    def test_upload_existing_user(self):
        """
        Check if uploading existing users ends up with them having new role
        assigned.

        This is a special case of upload feature: if user uploads a person that
        already exists we should only assign new role and event to that person.
        """
        csv = """personal,family,email,event,role
Harry,Potter,harry@hogwarts.edu,foobar,Helper
"""
        data, _ = upload_person_task_csv(StringIO(csv))

        # simulate user clicking "Use this user" next to matched person
        data[0]["existing_person_id"] = Person.objects.get(
            email="harry@hogwarts.edu"
        ).pk

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": data[0]["personal"],
            "family": data[0]["family"],
            "email": data[0]["email"],
            "event": data[0]["event"],
            "role": data[0]["role"],
            "confirm": "Confirm",
        }

        people_pre = set(Person.objects.all())
        tasks_pre = set(Task.objects.filter(person=self.harry, event__slug="foobar"))

        rv = self.client.post(
            reverse("person_bulk_add_confirmation"), payload, follow=True
        )
        self.assertEqual(rv.status_code, 200)

        people_post = set(Person.objects.all())
        tasks_post = set(Task.objects.filter(person=self.harry, event__slug="foobar"))

        # make sure no-one new was added
        self.assertSetEqual(people_pre, people_post)

        # make sure that Harry was assigned a new role
        self.assertNotEqual(tasks_pre, tasks_post)

    def test_upload_existing_user_existing_task(self):
        """
        Check if uploading existing user and assigning existing task to that
        user is silent (ie. no Task nor Person is being created).
        """
        foobar = Event.objects.get(slug="foobar")
        instructor = Role.objects.get(name="instructor")
        Task.objects.create(person=self.harry, event=foobar, role=instructor)

        csv = """personal,family,email,event,role
Harry,Potter,harry@hogwarts.edu,foobar,instructor
"""
        data, _ = upload_person_task_csv(StringIO(csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": data[0]["personal"],
            "family": data[0]["family"],
            "email": data[0]["email"],
            "event": data[0]["event"],
            "role": data[0]["role"],
            "confirm": "Confirm",
        }

        tasks_pre = set(Task.objects.filter(person=self.harry, event__slug="foobar"))
        users_pre = set(Person.objects.all())

        rv = self.client.post(
            reverse("person_bulk_add_confirmation"), payload, follow=True
        )

        tasks_post = set(Task.objects.filter(person=self.harry, event__slug="foobar"))
        users_post = set(Person.objects.all())
        self.assertEqual(tasks_pre, tasks_post)
        self.assertEqual(users_pre, users_post)
        self.assertEqual(rv.status_code, 200)

    def test_attendance_increases(self):
        """
        Check if uploading tasks with role "learner" increase event's
        attendance.
        """
        foobar = Event.objects.get(slug="foobar")
        self.assertEqual(foobar.attendance, 0)
        foobar.save()

        csv = """personal,family,email,event,role
Harry,Potter,harry@hogwarts.edu,foobar,learner
"""
        data, _ = upload_person_task_csv(StringIO(csv))

        # simulate user clicking "Use this user" next to matched person
        data[0]["existing_person_id"] = Person.objects.get(
            email="harry@hogwarts.edu"
        ).pk

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": data[0]["personal"],
            "family": data[0]["family"],
            "email": data[0]["email"],
            "event": data[0]["event"],
            "role": data[0]["role"],
            "confirm": "Confirm",
        }

        self.client.post(reverse("person_bulk_add_confirmation"), payload, follow=True)

        # instead of refreshing, we have to get a "fresh" object, because
        # `attendance` is a cached property
        foobar = Event.objects.get(slug="foobar")
        self.assertEqual(foobar.attendance, 1)


class BulkUploadRemoveEntryViewTestCase(CSVBulkUploadTestBase):
    def setUp(self):
        super().setUp()
        Role.objects.create(name="Helper")
        self.csv = """personal,family,email,event,role
Harry,Potter,harry@hogwarts.edu,foobar,learner
Hermione,Granger,hermione@hogwarts.edu,foobar,learner
Ron,Weasley,ron@hogwarts.edu,foobar,learner
"""

    def test_removing_entry0(self):
        """Make sure entries are removed by the view."""
        data, _ = upload_person_task_csv(StringIO(self.csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        self.client.get(reverse("person_bulk_add_remove_entry", args=[0]))

        # need to recreate session
        store = self.client.session
        data = store["bulk-add-people"]

        self.assertEqual(2, len(data))
        self.assertEqual(data[0]["personal"], "Hermione")
        self.assertEqual(data[1]["personal"], "Ron")

    def test_removing_entry1(self):
        """Make sure entries are removed by the view."""
        data, _ = upload_person_task_csv(StringIO(self.csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        self.client.get(reverse("person_bulk_add_remove_entry", args=[1]))

        # need to recreate session
        store = self.client.session
        data = store["bulk-add-people"]

        self.assertEqual(2, len(data))
        self.assertEqual(data[0]["personal"], "Harry")
        self.assertEqual(data[1]["personal"], "Ron")

    def test_removing_entry2(self):
        """Make sure entries are removed by the view."""
        data, _ = upload_person_task_csv(StringIO(self.csv))

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        self.client.get(reverse("person_bulk_add_remove_entry", args=[2]))

        # need to recreate session
        store = self.client.session
        data = store["bulk-add-people"]

        self.assertEqual(2, len(data))
        self.assertEqual(data[0]["personal"], "Harry")
        self.assertEqual(data[1]["personal"], "Hermione")


class BulkUploadMatchPersonViewTestCase(CSVBulkUploadTestBase):
    def setUp(self):
        super().setUp()
        Role.objects.create(name="Helper")
        self.csv = """personal,family,email,event,role
Harry,Potter,harry@hogwarts.edu,foobar,learner
Hermione,Granger,hermione@hogwarts.edu,foobar,learner
Ron,Weasley,ron@hogwarts.edu,foobar,learner
"""


class TestBulkUploadAddsEmailAction(FakeRedisTestCaseMixin, CSVBulkUploadTestBase):
    def setUp(self):
        super().setUp()
        Role.objects.create(name="host")

        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="automated-email"),
            ]
        )
        Organization.objects.bulk_create(
            [
                Organization(
                    domain="librarycarpentry.org", fullname="Library Carpentry"
                ),
                Organization(domain="carpentries.org", fullname="Instructor Training"),
            ]
        )
        test_event_1 = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="librarycarpentry.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
            address="Underground",
            latitude=20.0,
            longitude=20.0,
            url="https://test-event.example.com",
        )
        test_event_1.tags.set(
            Tag.objects.filter(name__in=["SWC", "DC", "LC", "automated-email"])
        )
        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(action="new-instructor", template=template)

        # save scheduler and connection data
        self._saved_scheduler = workshops.views.scheduler
        self._saved_redis_connection = workshops.views.redis_connection
        # overwrite them
        workshops.views.scheduler = self.scheduler
        workshops.views.redis_connection = self.connection

        self.csv = """personal,family,email,event,role
Harry,Potter,harry@hogwarts.edu,test-event,host
Hermione,Granger,hermione@hogwarts.edu,test-event,instructor
Ron,Weasley,ron@hogwarts.edu,test-event,instructor
"""

    def tearDown(self):
        super().tearDown()
        workshops.views.scheduler = self._saved_scheduler
        workshops.views.redis_connection = self._saved_redis_connection

    def test_jobs_created(self):
        data, _ = upload_person_task_csv(StringIO(self.csv))

        # simulate user clicking "Use this user" next to matched person
        data[0]["existing_person_id"] = Person.objects.get(
            email="harry@hogwarts.edu"
        ).pk
        data[1]["existing_person_id"] = Person.objects.get(
            email="hermione@granger.co.uk"
        ).pk
        data[2]["existing_person_id"] = Person.objects.get(
            email="rweasley@ministry.gov.uk"
        ).pk

        # self.client is authenticated user so we have access to the session
        store = self.client.session
        store["bulk-add-people"] = data
        store.save()

        # send exactly what's in 'data'
        payload = {
            "personal": [data[0]["personal"], data[1]["personal"], data[2]["personal"]],
            "family": [data[0]["family"], data[1]["family"], data[2]["family"]],
            "email": [data[0]["email"], data[1]["email"], data[2]["email"]],
            "event": [data[0]["event"], data[1]["event"], data[2]["event"]],
            "role": [data[0]["role"], data[1]["role"], data[2]["role"]],
            "confirm": "Confirm",
        }

        # empty tasks and no jobs scheduled
        tasks_pre = Task.objects.filter(
            person__in=Person.objects.filter(
                email__in=[
                    "harry@hogwarts.edu",
                    "hermione@granger.co.uk",
                    "rweasley@ministry.gov.uk",
                ]
            ),
            event__slug="test-event",
        )
        self.assertQuerysetEqual(tasks_pre, [])
        rqjobs_pre = RQJob.objects.all()
        self.assertQuerysetEqual(rqjobs_pre, [])

        # send data in
        rv = self.client.post(
            reverse("person_bulk_add_confirmation"), payload, follow=True
        )
        self.assertEqual(rv.status_code, 200)

        # 3 tasks created
        tasks_post = Task.objects.filter(
            person__in=Person.objects.filter(
                email__in=[
                    "harry@hogwarts.edu",
                    "hermione@granger.co.uk",
                    "rweasley@ministry.gov.uk",
                ]
            ),
            event__slug="test-event",
        )
        self.assertEqual(len(tasks_post), 3)
        # 2 jobs created (because only 2 entries have right role='instructor')
        rqjobs_post = RQJob.objects.all()
        self.assertEqual(len(rqjobs_post), 2)

        # ensure the job ids are mentioned in the page output
        content = rv.content.decode("utf-8")
        for job in rqjobs_post:
            self.assertIn(job.job_id, content)
