import datetime

from django.urls import reverse
from rest_framework.test import APITestCase

from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    KnowledgeDomain,
    Language,
    Organization,
    Person,
    Role,
    TrainingProgress,
    TrainingRequest,
    TrainingRequirement,
)


class BaseExportingTest(APITestCase):
    def setUp(self):
        # remove all existing badges (this will be rolled back anyway)
        # including swc-instructor and dc-instructor introduced by migration
        # 0064
        Badge.objects.all().delete()

    def setup_admin(self):
        self.admin = Person.objects.create_superuser(
            username="admin",
            personal="Super",
            family="User",
            email="sudo@example.org",
            password="admin",
        )
        self.admin.data_privacy_agreement = True
        self.admin.save()

    def login(self):
        if not hasattr(self, "admin"):
            self.setup_admin()
        self.client.login(username="admin", password="admin")


class TestExportingPersonData(BaseExportingTest):
    def setUp(self):
        # don't remove all badges
        # super().setUp()

        # prepare user
        self.user = Person(
            username="primary_user",
            personal="User",
            family="Primary",
            email="primary_user@amy.com",
            is_active=True,
            data_privacy_agreement=True,
        )
        self.user.set_password("password")
        self.user.save()

        # save API endpoint URL
        self.url = reverse("api:export-person-data")

    def login(self):
        """Overwrite BaseExportingTest's login method: instead of loggin in
        as an admin, use a normal user."""
        self.client.login(username="primary_user", password="password")

    def prepare_data(self, user):
        """Populate relational fields for the user."""

        # create and set airport for the user
        airport = Airport.objects.create(
            iata="DDD",
            fullname="Airport 55x105",
            country="CM",
            latitude=55.0,
            longitude=105.0,
        )
        self.user.airport = airport
        self.user.save()

        # create a fake organization
        test_host = Organization.objects.create(
            domain="example.com", fullname="Test Organization"
        )

        # create an event that will later be used
        event = Event.objects.create(
            start=datetime.date(2018, 6, 16),
            end=datetime.date(2018, 6, 17),
            slug="2018-06-16-AMY-event",
            host=test_host,
            url="http://example.org/2018-06-16-AMY-event",
        )

        # add a role
        Role.objects.create(name="instructor", verbose_name="Instructor")

        # add an admin user
        self.setup_admin()

        # award user some badges via awards (intermediary model)
        # one badge was awarded for the event
        Award.objects.create(
            person=self.user,
            badge=Badge.objects.get(name="swc-instructor"),
            event=event,
            awarded=datetime.date(2018, 6, 16),
        )
        # second badge was awarded without any connected event
        Award.objects.create(
            person=self.user,
            badge=Badge.objects.get(name="dc-instructor"),
            awarded=datetime.date(2018, 6, 16),
        )

        # user took part in the event as an instructor
        self.user.task_set.create(
            event=event,
            role=Role.objects.get(name="instructor"),
        )

        # user knows a couple of languages
        self.user.languages.set(Language.objects.filter(name__in=["English", "French"]))

        # add training requests
        training_request = TrainingRequest.objects.create(
            # mixins
            data_privacy_agreement=True,
            code_of_conduct_agreement=True,
            state="p",  # pending
            person=self.user,
            review_process="preapproved",
            group_name="Mosquitos",
            personal="User",
            middle="",
            family="Primary",
            email="primary_user@amy.com",
            secondary_email="not-used-often@amy.com",
            github="primary_user",
            occupation="undisclosed",
            occupation_other="",
            affiliation="AMY",
            location="Worldwide",
            country="W3",
            underresourced=False,
            # need to set it below
            # domains=KnowledgeDomain.objects.first(),
            domains_other="E-commerce",
            underrepresented="yes",
            underrepresented_details="LGBTQ",
            nonprofit_teaching_experience="Voluntary teacher",
            # need to set it below
            # previous_involvement=Role.objects.filter(name='instructor'),
            previous_training="course",
            previous_training_other="",
            previous_training_explanation="A course for voluntary teaching",
            previous_experience="ta",
            previous_experience_other="",
            previous_experience_explanation="After the course I became a TA",
            programming_language_usage_frequency="weekly",
            teaching_frequency_expectation="monthly",
            max_travelling_frequency="not-at-all",
            max_travelling_frequency_other="",
            reason="I want to became an instructor",
            user_notes="I like trains",
            training_completion_agreement=True,
            workshop_teaching_agreement=True,
        )
        training_request.domains.set([KnowledgeDomain.objects.first()])
        training_request.previous_involvement.set(
            Role.objects.filter(name="instructor")
        )

        # add some training progress
        TrainingProgress.objects.create(
            trainee=self.user,
            requirement=TrainingRequirement.objects.get(name="Discussion"),
            state="p",  # passed
            event=event,
            evaluated_by=None,
            discarded=False,
            url=None,
        )
        TrainingProgress.objects.create(
            trainee=self.user,
            requirement=TrainingRequirement.objects.get(name="DC Homework"),
            state="a",  # asked to repeat
            event=None,
            evaluated_by=self.admin,
            discarded=False,
            url="http://example.org/homework",
        )

    def test_unauthorized_access(self):
        """Make sure only authenticated users can access."""
        # logout
        self.client.logout()

        # retrieve endpoint
        rv = self.client.get(self.url)

        # make sure it's inaccessible
        self.assertEqual(rv.status_code, 401)

    def test_only_for_one_user(self):
        """Make sure the results are available only for the logged-in user,
        no-one else."""
        # prepare a different user
        self.second_user = Person(
            username="secondary_user",
            personal="User",
            family="Secondary",
            email="secondary_user@amy.com",
            is_active=True,
            data_privacy_agreement=True,
        )
        self.second_user.set_password("password")
        self.second_user.save()

        # login as first user
        self.client.login(username="primary_user", password="password")

        # retrieve endpoint
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)
        # make sure this endpoint returns current user data
        self.assertEqual(rv.json()["username"], "primary_user")

        # login as second user
        self.client.login(username="secondary_user", password="password")
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)
        # make sure this endpoint does not return first user data now
        self.assertEqual(rv.json()["username"], "secondary_user")

    def test_all_related_objects_shown(self):
        """Test if all related fields are present in data output."""
        self.login()

        # retrieve endpoint
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)

        # API results parsed as JSON
        user_data = rv.json()
        user_data_keys = user_data.keys()

        # make sure these fields are NOT in the API output
        missing_fields = [
            "password",
            "is_active",
        ]

        # simple (non-relational) fields expected in API output
        expected_fields = [
            "data_privacy_agreement",
            "personal",
            "middle",
            "family",
            "email",
            "username",
            "gender",
            "may_contact",
            "publish_profile",
            "github",
            "twitter",
            "url",
            "user_notes",
            "affiliation",
            "occupation",
            "orcid",
        ]

        # relational fields expected in API output
        expected_relational = [
            "airport",
            "badges",
            "lessons",
            "domains",
            "languages",
            "tasks",  # renamed in serializer (was: task_set)
            "awards",  # renamed in serializer (was: award_set)
            "training_requests",  # renamed from "trainingrequest_set"
            "training_progresses",  # renamed from "trainingprogress_set"
        ]

        # ensure missing fields are not to be found in API output
        for field in missing_fields:
            self.assertNotIn(field, user_data_keys)

        # ensure required fields are present
        for field in expected_fields + expected_relational:
            self.assertIn(field, user_data_keys)

    def test_relational_fields_structure(self):
        """Make sure relational fields available via API endpoints
        retain a specific structure."""
        self.prepare_data(user=self.user)
        self.login()

        # retrieve endpoint
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)

        # API results parsed as JSON
        data = rv.json()

        # expected data dict
        expected = dict()

        # test expected Airport output
        expected["airport"] = {
            "iata": "DDD",
            "fullname": "Airport 55x105",
            "country": "CM",
            "latitude": 55.0,
            "longitude": 105.0,
        }
        self.assertEqual(data["airport"], expected["airport"])

        # test expected Badges output
        expected["badges"] = [
            {
                "name": "swc-instructor",
                "title": "Software Carpentry Instructor",
                "criteria": "Teaching at Software Carpentry workshops or" " online",
            },
            {
                "name": "dc-instructor",
                "title": "Data Carpentry Instructor",
                "criteria": "Teaching at Data Carpentry workshops or" " online",
            },
        ]
        self.assertEqual(data["badges"], expected["badges"])

        # test expected Awards output
        expected["awards"] = [
            {
                "badge": "swc-instructor",
                "awarded": "2018-06-16",
                "event": {
                    "slug": "2018-06-16-AMY-event",
                    "start": "2018-06-16",
                    "end": "2018-06-17",
                    "tags": [],
                    "website_url": "http://example.org/2018-06-16-AMY-event",
                    "venue": "",
                    "address": "",
                    "country": "",
                    "latitude": None,
                    "longitude": None,
                },
            },
            {
                "badge": "dc-instructor",
                "awarded": "2018-06-16",
                "event": None,
            },
        ]
        self.assertEqual(data["awards"], expected["awards"])

        # test expected Tasks output
        expected["tasks"] = [
            {
                "event": {
                    "slug": "2018-06-16-AMY-event",
                    "start": "2018-06-16",
                    "end": "2018-06-17",
                    "tags": [],
                    "website_url": "http://example.org/2018-06-16-AMY-event",
                    "venue": "",
                    "address": "",
                    "country": "",
                    "latitude": None,
                    "longitude": None,
                },
                "role": "instructor",
            },
        ]
        self.assertEqual(data["tasks"], expected["tasks"])

        # test expected Languages output
        expected["languages"] = [
            "English",
            "French",
        ]
        self.assertEqual(data["languages"], expected["languages"])

        # test expected TrainingRequests output
        expected["training_requests"] = [
            {
                # these are generated by Django, so we borrow them from the
                # output
                "created_at": data["training_requests"][0]["created_at"],
                "last_updated_at": data["training_requests"][0]["last_updated_at"],
                "state": "Pending",
                "review_process": "preapproved",
                "group_name": "Mosquitos",
                "personal": "User",
                "middle": "",
                "family": "Primary",
                "email": "primary_user@amy.com",
                "secondary_email": "not-used-often@amy.com",
                "github": "primary_user",
                "occupation": "undisclosed",
                "occupation_other": "",
                "affiliation": "AMY",
                "location": "Worldwide",
                "country": "W3",
                "underresourced": False,
                "domains": ["Chemistry"],
                "domains_other": "E-commerce",
                "underrepresented": "yes",
                "underrepresented_details": "LGBTQ",
                "nonprofit_teaching_experience": "Voluntary teacher",
                "previous_involvement": ["instructor"],
                "previous_training": "A certification or short course",
                "previous_training_other": "",
                "previous_training_explanation": "A course for voluntary teaching",
                "previous_experience": "Teaching assistant for a full course",
                "previous_experience_other": "",
                "previous_experience_explanation": "After the course I became a TA",
                "programming_language_usage_frequency": "A few times a week",
                "teaching_frequency_expectation": "Several times a year",
                "teaching_frequency_expectation_other": "",
                "max_travelling_frequency": "Not at all",
                "max_travelling_frequency_other": "",
                "reason": "I want to became an instructor",
                "user_notes": "I like trains",
                "training_completion_agreement": True,
                "workshop_teaching_agreement": True,
                "data_privacy_agreement": True,
                "code_of_conduct_agreement": True,
            }
        ]

        self.assertEqual(len(data["training_requests"]), 1)
        self.assertEqual(data["training_requests"][0], expected["training_requests"][0])

        # test expected TrainingProgress output
        expected["training_progresses"] = [
            {
                # these are generated by Django, so we borrow them from the
                # output
                "created_at": data["training_progresses"][0]["created_at"],
                "last_updated_at": data["training_progresses"][0]["last_updated_at"],
                "requirement": {
                    "name": "Discussion",
                    "url_required": False,
                    "event_required": False,
                },
                "state": "Passed",
                "discarded": False,
                "evaluated_by": None,
                "event": {
                    "slug": "2018-06-16-AMY-event",
                    "start": "2018-06-16",
                    "end": "2018-06-17",
                    "tags": [],
                    "website_url": "http://example.org/2018-06-16-AMY-event",
                    "venue": "",
                    "address": "",
                    "country": "",
                    "latitude": None,
                    "longitude": None,
                },
                "url": None,
            },
            {
                # these are generated by Django, so we borrow them from the
                # output
                "created_at": data["training_progresses"][1]["created_at"],
                "last_updated_at": data["training_progresses"][1]["last_updated_at"],
                "requirement": {
                    "name": "DC Homework",
                    "url_required": True,
                    "event_required": False,
                },
                "state": "Asked to repeat",
                "discarded": False,
                "evaluated_by": {
                    "name": "Super User",
                },
                "event": None,
                "url": "http://example.org/homework",
            },
        ]
        self.assertEqual(len(data["training_progresses"]), 2)
        self.assertEqual(
            data["training_progresses"][0], expected["training_progresses"][0]
        )
        self.assertEqual(
            data["training_progresses"][1], expected["training_progresses"][1]
        )
