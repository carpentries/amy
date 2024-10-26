import datetime
from typing import List

from django.urls import reverse
from rest_framework.test import APITestCase

from consents.models import Consent, Term
from trainings.models import Involvement
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
from workshops.tests.base import consent_to_all_required_consents


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
        consent_to_all_required_consents(self.admin)

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
        )
        self.user.set_password("password")
        self.user.save()
        consent_to_all_required_consents(self.user)

        # save API endpoint URL
        self.url = reverse("api-v1:export-person-data")

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
            member_code="Mosquitos",
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
            checkout_intent="yes",
            teaching_intent="yes-central",
            programming_language_usage_frequency="weekly",
            teaching_frequency_expectation="monthly",
            max_travelling_frequency="not-at-all",
            max_travelling_frequency_other="",
            reason="I want to became an instructor",
            user_notes="I like trains",
        )
        training_request.domains.set([KnowledgeDomain.objects.first()])
        training_request.previous_involvement.set(
            Role.objects.filter(name="instructor")
        )

        # add some training progress
        TrainingProgress.objects.create(
            trainee=self.user,
            requirement=TrainingRequirement.objects.get(name="Welcome Session"),
            state="p",  # passed
            event=event,
            url=None,
        )
        get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved",
            defaults={
                "url_required": False,
                "event_required": False,
                "involvement_required": True,
            },
        )
        github_contribution, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution",
            defaults={
                "display_name": "Submitted a contribution to a Carpentries repository",
                "url_required": True,
                "date_required": True,
            },
        )
        TrainingProgress.objects.create(
            trainee=self.user,
            requirement=get_involved,
            involvement_type=github_contribution,
            state="a",  # asked to repeat
            event=None,
            url="https://github.com/carpentries",
            date=datetime.date(2023, 5, 31),
            trainee_notes="Notes submitted by trainee",
        )
        terms = (
            Term.objects.active()
            .filter(required_type=Term.PROFILE_REQUIRE_TYPE)
            .prefetch_active_options()
        )
        consents = Consent.objects.filter(person=self.user).active()
        consents_by_term_id = {consent.term_id: consent for consent in consents}
        self.user_consents: List[Consent] = []
        for term in terms:
            self.user_consents.append(
                Consent.reconsent(
                    consent=consents_by_term_id[term.pk], term_option=term.options[0]
                )
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
        )
        self.second_user.set_password("password")
        self.second_user.save()
        consent_to_all_required_consents(self.second_user)

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
            "personal",
            "middle",
            "family",
            "email",
            "username",
            "gender",
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
            "consents",  # renamed from "consent_set"
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

        # test expected Consents output
        user_consents = Consent.objects.active().filter(person=self.user)
        self.assertCountEqual(
            [consent.term.slug for consent in user_consents],
            [consent["term"]["slug"] for consent in data["consents"]],
        )
        may_publish_name = [
            consent
            for consent in user_consents
            if consent.term.slug == "may-publish-name"
        ][0]
        public_profile = [
            consent
            for consent in user_consents
            if consent.term.slug == "public-profile"
        ][0]
        # assert consent format -- no term option
        self.assertIn(
            {
                "term": {
                    "content": may_publish_name.term.content,
                    "help_text": may_publish_name.term.help_text,
                    "required_type": may_publish_name.term.required_type,
                    "slug": may_publish_name.term.slug,
                },
                "term_option": None,
            },
            data["consents"],
        )
        # assert consent format -- with term option
        self.assertIn(
            {
                "term": {
                    "content": public_profile.term.content,
                    "help_text": public_profile.term.help_text,
                    "required_type": public_profile.term.required_type,
                    "slug": public_profile.term.slug,
                },
                "term_option": str(public_profile.term_option),
            },
            data["consents"],
        )
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
                "member_code": "Mosquitos",
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
                "checkout_intent": "Yes",
                "teaching_intent": "Yes - I plan to volunteer with The Carpentries "
                "to teach workshops for other communities",
                "teaching_frequency_expectation": "Several times a year",
                "teaching_frequency_expectation_other": "",
                "max_travelling_frequency": "Not at all",
                "max_travelling_frequency_other": "",
                "reason": "I want to became an instructor",
                "user_notes": "I like trains",
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
                    "name": "Welcome Session",
                    "url_required": False,
                    "event_required": False,
                    "involvement_required": False,
                },
                "involvement_type": None,
                "state": "Passed",
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
                "date": None,
                "trainee_notes": "",
            },
            {
                # these are generated by Django, so we borrow them from the
                # output
                "created_at": data["training_progresses"][1]["created_at"],
                "last_updated_at": data["training_progresses"][1]["last_updated_at"],
                "requirement": {
                    "name": "Get Involved",
                    "url_required": False,
                    "event_required": False,
                    "involvement_required": True,
                },
                "involvement_type": {
                    "name": "GitHub Contribution",
                    "display_name": "Submitted a contribution to a Carpentries repository on GitHub",  # noqa
                    "url_required": True,
                    "date_required": True,
                    "notes_required": False,
                },
                "state": "Asked to repeat",
                "event": None,
                "url": "https://github.com/carpentries",
                "date": "2023-05-31",
                "trainee_notes": "Notes submitted by trainee",
            },
        ]
        self.assertEqual(len(data["training_progresses"]), 2)
        self.assertEqual(
            data["training_progresses"][0], expected["training_progresses"][0]
        )
        self.assertEqual(
            data["training_progresses"][1], expected["training_progresses"][1]
        )
