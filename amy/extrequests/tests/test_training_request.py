from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock
from urllib.parse import urlencode

from django.contrib.messages import WARNING
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import reverse
from django_comments.models import Comment

from consents.models import (
    Consent,
    Term,
    TermEnum,
    TermOption,
    TermOptionChoices,
    TrainingRequestConsent,
)
from extrequests.forms import TrainingRequestsMergeForm
from extrequests.views import _match_training_request_to_person
from workshops.models import (
    Event,
    KnowledgeDomain,
    Member,
    MemberRole,
    Membership,
    Organization,
    Person,
    Role,
    Tag,
    Task,
    TrainingRequest,
)
from workshops.tests.base import TestBase


def create_training_request(state, person, open_review=True, reg_code=""):
    return TrainingRequest.objects.create(
        review_process="open" if open_review else "preapproved",
        member_code=reg_code,
        personal="John",
        family="Smith",
        email="john@smith.com",
        occupation="",
        affiliation="AGH University of Science and Technology",
        location="Cracow",
        country="PL",
        previous_training="none",
        previous_experience="none",
        programming_language_usage_frequency="daily",
        checkout_intent="yes",
        teaching_intent="yes-central",
        reason="Just for fun.",
        teaching_frequency_expectation="monthly",
        max_travelling_frequency="yearly",
        state=state,
        person=person,
        data_privacy_agreement=True,
    )


class TestTrainingRequestModel(TestBase):
    def setUp(self):
        # create admin account
        self._setUpUsersAndLogin()

        # create trainee account
        self._setUpRoles()
        self._setUpTags()

        self.trainee = Person.objects.create_user(
            username="trainee", personal="Bob", family="Smith", email="bob@smith.com"
        )
        org = Organization.objects.create(domain="example.com", fullname="Test Organization")
        training = Event.objects.create(slug="training", host=org)
        training.tags.add(Tag.objects.get(name="TTT"))
        learner = Role.objects.get(name="learner")
        Task.objects.create(person=self.trainee, event=training, role=learner)

    def test_accepted_request_are_always_valid(self):
        """Accepted training requests are valid regardless of whether they
        are matched to a training."""
        req = create_training_request(state="a", person=None)
        req.full_clean()

        req = create_training_request(state="a", person=self.admin)
        req.full_clean()

        req = create_training_request(state="a", person=self.trainee)
        req.full_clean()

    def test_valid_pending_request(self):
        req = create_training_request(state="p", person=None)
        req.full_clean()

        req = create_training_request(state="p", person=self.admin)
        req.full_clean()

    def test_pending_request_must_not_be_matched(self):
        req = create_training_request(state="p", person=self.trainee)
        with self.assertRaises(ValidationError):
            req.full_clean()


class TestTrainingRequestModelScoring(TestBase):
    def setUp(self):
        self._setUpRoles()

        self.tr = TrainingRequest.objects.create(
            personal="John",
            family="Smith",
            email="john@smith.com",
            occupation="",
            affiliation="",
            location="Washington",
            country="US",
            previous_training="none",
            previous_experience="none",
            programming_language_usage_frequency="never",
            reason="Just for fun.",
            teaching_frequency_expectation="monthly",
            max_travelling_frequency="yearly",
            state="p",
        )

    def test_minimal_response_no_score(self):
        self.assertEqual(self.tr.score_auto, 0)

    def test_country(self):
        # a sample country that scores a point
        self.tr.country = "W3"
        self.tr.save()
        self.assertEqual(self.tr.score_auto, 1)

    def test_underresourced_institution(self):
        # a sample country that scores a point
        self.tr.underresourced = True
        self.tr.save()
        self.assertEqual(self.tr.score_auto, 1)

    def test_country_and_underresourced_institution(self):
        # a sample country that scores a point
        self.tr.country = "W3"
        self.tr.underresourced = True
        self.tr.save()
        self.assertEqual(self.tr.score_auto, 2)

    def test_domains(self):
        """Ensure m2m_changed signals work correctly on
        `TrainingRequest.domains` field."""
        # test adding a domain
        domain = KnowledgeDomain.objects.get(name="Humanities")
        self.tr.domains.add(domain)
        self.assertEqual(self.tr.score_auto, 1)

        # test removing a domain
        # domain.trainingrequest_set.remove(self.tr)
        self.tr.domains.remove(domain)
        self.assertEqual(len(self.tr.domains.all()), 0)
        self.assertEqual(self.tr.score_auto, 0)

        # test setting domains
        domains = KnowledgeDomain.objects.filter(
            name__in=[
                "Humanities",
                "Library and information science",
                "Economics/business",
                "Social sciences",
                "Chemistry",
            ]
        )
        self.tr.domains.set(domains)
        self.assertEqual(self.tr.score_auto, 1)

    def test_each_domain(self):
        "Ensure each domain from the list counts for +1 score_auto."
        domain_names = [
            "Humanities",
            "Library and information science",
            "Economics/business",
            "Social sciences",
            "Chemistry",
        ]

        last_domain = None

        for name in domain_names:
            # we need to remove last domain added, but we can't use `.clear`
            # because it doesn't trigger the m2m_changed signal
            if last_domain:
                self.tr.domains.remove(last_domain)

            self.assertEqual(self.tr.score_auto, 0, name)
            last_domain = KnowledgeDomain.objects.get(name=name)
            self.tr.domains.add(last_domain)
            self.assertEqual(self.tr.score_auto, 1, name)

    def test_underrepresented(self):
        """With change in https://github.com/swcarpentry/amy/issues/1468,
        we start automatically scoring underrepresented field."""
        data = {
            "yes": 1,
            "no": 0,
            "undisclosed": 0,
            "???": 0,
        }
        for value, score in data.items():
            self.tr.underrepresented = value
            self.tr.save()
            self.assertEqual(self.tr.score_auto, score)

    def test_previous_involvement(self):
        """Ensure m2m_changed signals work correctly on
        `TrainingRequest.previous_involvement` field."""
        roles = Role.objects.all()
        self.tr.previous_involvement.add(roles[0])
        self.assertEqual(self.tr.score_auto, 1)
        self.tr.previous_involvement.add(roles[1])
        self.assertEqual(self.tr.score_auto, 2)
        self.tr.previous_involvement.add(roles[2])
        self.assertEqual(self.tr.score_auto, 3)
        self.tr.previous_involvement.add(roles[3])
        # previous involvement scoring max's out at 3
        self.assertEqual(self.tr.score_auto, 3)

    def test_previous_training_in_teaching(self):
        """Go through all options in `previous_training` and ensure only some
        produce additional score."""
        choices = TrainingRequest.PREVIOUS_TRAINING_CHOICES
        for choice, desc in choices:
            self.tr.previous_training = choice
            self.tr.save()
            if choice in ["course", "full"]:
                self.assertEqual(self.tr.score_auto, 1)
            else:
                self.assertEqual(self.tr.score_auto, 0)

    def test_previous_experience_in_teaching(self):
        """Go through all options in `previous_experience` and ensure only some
        produce additional score."""
        choices = TrainingRequest.PREVIOUS_EXPERIENCE_CHOICES
        for choice, desc in choices:
            self.tr.previous_experience = choice
            self.tr.save()
            if choice in ["ta", "courses"]:
                self.assertEqual(self.tr.score_auto, 1)
            else:
                self.assertEqual(self.tr.score_auto, 0)

    def test_tooling(self):
        """Go through all options in `programming_language_usage_frequency`
        and ensure only some produce additional score."""
        choices = TrainingRequest.PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES
        for choice, desc in choices:
            self.tr.programming_language_usage_frequency = choice
            self.tr.save()
            if choice in ["daily", "weekly"]:
                self.assertEqual(self.tr.score_auto, 1)
            else:
                self.assertEqual(self.tr.score_auto, 0)


class TestTrainingRequestsListView(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        self.first_req = create_training_request(state="d", person=self.spiderman)
        self.second_req = create_training_request(state="p", person=None)
        self.third_req = create_training_request(state="a", person=self.ironman)
        self.org = Organization.objects.create(domain="example.com", fullname="Test Organization")
        self.learner = Role.objects.get(name="learner")
        self.ttt = Tag.objects.get(name="TTT")

        self.first_training = Event.objects.create(slug="ttt-event", host=self.org)
        self.first_training.tags.add(self.ttt)
        Task.objects.create(person=self.spiderman, role=self.learner, event=self.first_training)
        self.second_training = Event.objects.create(slug="second-ttt-event", host=self.org)
        self.second_training.tags.add(self.ttt)

    def test_view_loads(self):
        """
        View should default to settings:
            state=pa (Pending or accepted)
            matched=u (Unmatched)
        """
        # Act
        rv = self.client.get(reverse("all_trainingrequests"))

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(
            set(rv.context["requests"]),
            {self.second_req},
        )

    def test_view_loads_all_on_request(self):
        """
        Explicitly setting state and matched to null should return all requests.
        """
        # Arrange
        query_string = "state=&matched="

        # Act
        rv = self.client.get(reverse("all_trainingrequests"), QUERY_STRING=query_string)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(
            set(rv.context["requests"]),
            {self.first_req, self.second_req, self.third_req},
        )

    def test_successful_bulk_discard(self):
        data = {
            "discard": "",
            "requests": [self.first_req.pk, self.second_req.pk],
        }
        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Successfully discarded selected requests."
        self.assertContains(rv, msg)
        self.first_req.refresh_from_db()
        self.assertEqual(self.first_req.state, "d")
        self.second_req.refresh_from_db()
        self.assertEqual(self.second_req.state, "d")
        self.third_req.refresh_from_db()
        self.assertEqual(self.third_req.state, "a")

    def test_successful_bulk_accept(self):
        data = {
            "accept": "",
            "requests": [self.first_req.pk, self.second_req.pk],
        }
        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Successfully accepted selected requests."
        self.assertContains(rv, msg)
        self.first_req.refresh_from_db()
        self.assertEqual(self.first_req.state, "a")
        self.second_req.refresh_from_db()
        self.assertEqual(self.second_req.state, "a")
        self.third_req.refresh_from_db()
        self.assertEqual(self.third_req.state, "a")

    def test_successful_matching_to_training(self):
        data = {
            "match": "",
            "event": self.second_training.pk,
            "requests": [self.first_req.pk],
            "seat_public": "True",
        }
        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Successfully accepted and matched selected people to training."
        self.assertContains(rv, msg)
        self.assertEqual(
            set(Event.objects.filter(task__person=self.spiderman, task__role__name="learner")),
            {self.first_training, self.second_training},
        )
        self.assertEqual(
            set(Event.objects.filter(task__person=self.ironman, task__role__name="learner")),
            set(),
        )

    def test_successful_matching_twice_to_the_same_training(self):
        data = {
            "match": "",
            "event": self.first_training.pk,
            "requests": [self.first_req.pk],
        }
        # Spiderman is already matched with first_training
        assert self.spiderman.get_training_tasks()[0].event == self.first_training

        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Successfully accepted and matched selected people to training."
        self.assertContains(rv, msg)
        self.assertEqual(
            set(Event.objects.filter(task__person=self.spiderman, task__role__name="learner")),
            {self.first_training},
        )

    def test_trainee_accepted_during_matching(self):
        # this request is set up without matched person
        self.second_req.person = self.spiderman
        self.second_req.save()
        self.assertEqual(self.second_req.state, "p")

        data = {
            "match": "",
            "event": self.second_training.pk,
            "requests": [self.second_req.pk],
            "seat_public": "True",
        }
        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Successfully accepted and matched selected people to training."
        self.assertContains(rv, msg)
        self.second_req.refresh_from_db()
        self.assertEqual(self.second_req.state, "a")

    def test_matching_to_training_fails_in_the_case_of_unmatched_persons(self):
        """Requests that are not matched with any trainee account cannot be
        matched with a training."""

        data = {
            "match": "",
            "event": self.second_training.pk,
            "requests": [self.first_req.pk, self.second_req.pk],
        }
        # Spiderman is already matched with first_training
        assert self.spiderman.get_training_tasks()[0].event == self.first_training

        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Fix errors in the form below and try again."
        self.assertContains(rv, msg)
        msg = (
            "Some of the requests are not matched to a trainee yet. Before "
            "matching them to a training, you need to accept them "
            "and match with a trainee."
        )
        self.assertContains(rv, msg)
        # Check that Spiderman is not matched to second_training even though
        # he was selected.
        self.assertEqual(
            set(Event.objects.filter(task__person=self.spiderman, task__role__name="learner")),
            {self.first_training},
        )

    def test_successful_unmatching(self):
        data = {
            "unmatch": "",
            "requests": [self.first_req.pk],
        }
        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Successfully unmatched selected people from trainings."
        self.assertContains(rv, msg)

        self.assertEqual(
            set(Event.objects.filter(task__person=self.spiderman, task__role__name="learner")),
            set(),
        )

    def test_unmatching_fails_when_no_matched_trainee(self):
        """Requests that are not matched with any trainee cannot be
        unmatched from a training."""

        data = {
            "unmatch": "",
            "requests": [self.first_req.pk, self.second_req.pk],
        }
        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        msg = "Fix errors in the form below and try again."
        self.assertContains(rv, msg)

        # Check that Spiderman is still matched to first_training even though
        # he was selected.
        self.assertEqual(
            set(Event.objects.filter(task__person=self.spiderman, task__role__name="learner")),
            {self.first_training},
        )

    def test_matching_no_remaining__no_message(self):
        """Regression test for
        https://github.com/carpentries/amy/issues/1946#issuecomment-875806218.

        Basically when matching the steps were:
        1. create N tasks
        2. check if remaining is less than or equal to N
           (remaining - requests_count <= 0)

        This was prone to error since remaining already was reduced by N - when tasks
        were created."""
        # Arrange
        # create 2 memberships with various number of seats
        # (2 memberships are required because of @cached_property used in one of the
        # fields)
        membership1 = Membership.objects.create(
            variant="partner",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            public_instructor_training_seats=3,
        )
        membership2 = Membership.objects.create(
            variant="partner",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            public_instructor_training_seats=1,
        )
        Member.objects.create(
            membership=membership1,
            organization=self.org,
            role=MemberRole.objects.first(),
        )
        data1 = {
            "match": "",
            "requests": [self.first_req.pk, self.third_req.pk],
            "event": self.second_training.pk,
            "seat_membership": membership1.pk,
            "seat_public": True,
        }
        msg1 = f"Membership &quot;{membership1}&quot; is using more training seats " "than it&#x27;s been allowed."
        self.second_req.person = self.blackwidow
        self.second_req.save()
        data2 = {
            "match": "",
            "requests": [self.second_req.pk],
            "event": self.second_training.pk,
            "seat_membership": membership2.pk,
            "seat_public": True,
        }
        msg2 = f"Membership &quot;{membership2}&quot; is using more training seats " "than it&#x27;s been allowed."

        # Act
        rv1 = self.client.post(reverse("all_trainingrequests"), data1, follow=True)
        rv2 = self.client.post(reverse("all_trainingrequests"), data2, follow=True)

        # Assert
        self.assertEqual(membership1.public_instructor_training_seats_remaining, 1)
        self.assertNotContains(rv1, msg1)
        self.assertEqual(membership2.public_instructor_training_seats_remaining, 0)
        self.assertContains(rv2, msg2)

    def test_inhouse_created_successfully(self):
        """Regression test: in-house seat can be created successfully."""
        # Arrange
        membership = Membership.objects.create(
            variant="partner",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            public_instructor_training_seats=1,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org,
            role=MemberRole.objects.first(),
        )
        data = {
            "match": "",
            "requests": [self.first_req.pk],
            "event": self.second_training.pk,
            "seat_membership": membership.pk,
            "seat_public": False,  # this should create an in-house seat
        }

        # Act
        self.client.post(reverse("all_trainingrequests"), data, follow=True)

        # Assert
        task = Task.objects.get(person=self.first_req.person, event=self.second_training)
        self.assertEqual(task.seat_public, data["seat_public"])

    def test_auto_assign_membership_seats(self):
        """Test that the bulk form can match multiple trainees to different memberships
        according to member code."""
        # Arrange
        # set up some memberships
        membership_alpha = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            registration_code="alpha44",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            public_instructor_training_seats=2,
        )
        membership_beta = Membership.objects.create(
            name="Beta Organization",
            variant="bronze",
            registration_code="beta55",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            public_instructor_training_seats=0,
        )
        # create some requests for these codes
        req1 = create_training_request("p", self.blackwidow, open_review=False, reg_code="alpha44")
        req2 = create_training_request("p", self.ironman, open_review=False, reg_code="beta55")
        req3 = create_training_request("p", self.spiderman, open_review=False, reg_code="invalid")

        data = {
            "match": "",
            "event": self.first_training.pk,
            "seat_membership_auto_assign": "True",
            "requests": [req1.pk, req2.pk, req3.pk, self.first_req.pk],
            "seat_public": "True",
        }

        # Act
        rv = self.client.post(reverse("all_trainingrequests"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainingrequests")
        self.assertNotContains(rv, "Successfully accepted and matched selected people to training")
        self.assertContains(rv, "Accepted and matched 2 people to training")
        self.assertContains(rv, "raised 1 warning")
        self.assertContains(rv, "2 request(s) were skipped due to errors")
        self.assertEqual(Task.objects.filter(seat_membership=membership_alpha).count(), 1)
        self.assertEqual(Task.objects.filter(seat_membership=membership_beta).count(), 1)
        self.assertContains(rv, "No membership found for registration code &quot;invalid&quot;")
        self.assertContains(
            rv,
            "Request does not include a member registration " "code, so cannot be matched to a membership seat.",
        )


class TestMatchingTrainingRequestAndDetailedView(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpAirports()
        self._setUpNonInstructors()

    def test_detailed_view_of_pending_request(self):
        """Match Request form should be displayed only when no account is
        matched."""
        req = create_training_request(state="p", person=None)
        rv = self.client.get(reverse("trainingrequest_details", args=[req.pk]))
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, "Match Request to AMY account")

    def test_detailed_view_of_accepted_request(self):
        """Match Request form should be displayed only when no account is
        matched."""
        req = create_training_request(state="p", person=self.admin)
        rv = self.client.get(reverse("trainingrequest_details", args=[req.pk]))
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, "Match Request to AMY account")

    def test_person_is_suggested(self):
        req = create_training_request(state="p", person=None)
        p = Person.objects.create_user(
            username="john_smith",
            personal="john",
            family="smith",
            email="asdf@gmail.com",
        )
        rv = self.client.get(reverse("trainingrequest_details", args=[req.pk]))

        self.assertEqual(rv.context["form"].initial["person"], p)

    def test_person_is_suggested_based_on_secondary_email(self):
        """Having just secondary email matching should show the person
        in results."""
        req = create_training_request(state="p", person=None)
        p = Person.objects.create(
            username="john_kowalsky",
            personal="Johnny",
            family="Kowalsky",
            email="asdf@gmail.com",
            secondary_email="john@smith.com",
        )
        rv = self.client.get(reverse("trainingrequest_details", args=[req.pk]))

        self.assertEqual(rv.context["form"].initial["person"], p)

    def test_new_person(self):
        req = create_training_request(state="p", person=None)
        rv = self.client.get(reverse("trainingrequest_details", args=[req.pk]))

        self.assertEqual(rv.context["form"].initial["person"], None)

    def test_matching_with_existing_account_works(self):
        """Regression test for [#949].

        [#949] https://github.com/swcarpentry/amy/pull/949/"""

        req = create_training_request(state="p", person=None)
        rv = self.client.post(
            reverse("trainingrequest_details", args=[req.pk]),
            data={"person": self.ironman.pk, "match-selected-person": ""},
            follow=True,
        )
        self.assertEqual(rv.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.state, "p")
        self.assertEqual(req.person, self.ironman)

        self.ironman.refresh_from_db()

        # in response to #1270, check if person record was updated
        data_expected = {
            "personal": req.personal,
            "middle": req.middle,
            "family": req.family,
            "email": req.email,
            "country": req.country,
            "github": req.github or None,
            "affiliation": req.affiliation,
            "occupation": req.get_occupation_display() if req.occupation else req.occupation_other,
            "is_active": True,
        }
        for key, value in data_expected.items():
            self.assertEqual(getattr(self.ironman, key), value, "Attribute: {}".format(key))

        self.assertEqual(set(self.ironman.domains.all()), set(req.domains.all()))

    def test_matching_with_new_account_works(self):
        req = create_training_request(state="p", person=None)
        rv = self.client.post(
            reverse("trainingrequest_details", args=[req.pk]),
            data={"create-new-person": ""},
            follow=True,
        )
        self.assertEqual(rv.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.state, "p")

        # in response to #1270, check if person record was updated
        data_expected = {
            "personal": req.personal,
            "middle": req.middle,
            "family": req.family,
            "email": req.email,
            "country": req.country,
            "github": req.github or None,
            "affiliation": req.affiliation,
            "occupation": req.get_occupation_display() if req.occupation else req.occupation_other,
            "is_active": True,
        }
        for key, value in data_expected.items():
            self.assertEqual(getattr(req.person, key), value, "Attribute: {}".format(key))

        self.assertEqual(set(req.person.domains.all()), set(req.domains.all()))

    def test_matching_updates_consents(self) -> None:
        # Arrange
        req = create_training_request(state="p", person=None)
        may_contact_term = Term.objects.get_by_key(TermEnum.MAY_CONTACT)
        privacy_policy_term = Term.objects.get_by_key(TermEnum.PRIVACY_POLICY)
        public_profile_term = Term.objects.get_by_key(TermEnum.PUBLIC_PROFILE)
        TrainingRequestConsent.objects.create(
            training_request=req,
            term=may_contact_term,
            term_option=TermOption.objects.filter(term=may_contact_term).get_decline_term_option(),
        )
        TrainingRequestConsent.objects.create(
            training_request=req,
            term=privacy_policy_term,
            term_option=TermOption.objects.filter(term=privacy_policy_term).get_agree_term_option(),
        )
        TrainingRequestConsent.objects.create(
            training_request=req,
            term=public_profile_term,
            term_option=TermOption.objects.filter(term=public_profile_term).get_agree_term_option(),
        )

        # Act
        rv = self.client.post(
            reverse("trainingrequest_details", args=[req.pk]),
            data={"person": self.ironman.pk, "match-selected-person": ""},
            follow=True,
        )

        # Assert
        self.assertEqual(rv.status_code, 200)
        req.refresh_from_db()
        Consent.objects.active().get(
            person=req.person,
            term=may_contact_term,
            term_option__option_type=TermOptionChoices.DECLINE,
        )
        Consent.objects.active().get(
            person=req.person,
            term=privacy_policy_term,
            term_option__option_type=TermOptionChoices.AGREE,
        )
        Consent.objects.active().get(
            person=req.person,
            term=public_profile_term,
            term_option__option_type=TermOptionChoices.AGREE,
        )

    def test_matching_in_transaction(self):
        """This is a regression test.

        In case of automatic person data rewrite, when matching a Training
        Request with Person, uniqueness constraint can be broken. In such
        scenario AMY must inform correctly about the issue, not throw 500
        error."""
        # this email conflicts with `duplicate` person below
        tr = create_training_request(state="p", person=None)
        tr.personal = "John"
        tr.family = "Smith"
        tr.email = "john@corporate.edu"
        tr.save()

        # a fake request
        factory = RequestFactory()
        request = factory.get("/")  # doesn't really matter where
        # adding session middleware, because it's required by messages
        session_middleware = SessionMiddleware(MagicMock())
        session_middleware.process_request(request)
        request.session.save()
        # adding messages because they're used in
        # _match_training_request_to_person
        messages_middleware = MessageMiddleware(MagicMock())
        messages_middleware.process_request(request)

        create = False
        person = Person.objects.create(
            username="john_smith",
            personal="john",
            family="smith",
            email="john@smith.com",
        )
        # duplicate
        Person.objects.create(
            username="jonny_smith",
            personal="jonny",
            family="smith",
            email="john@corporate.edu",
        )

        # matching fails because it can't rewrite email address due to
        # uniqueness constraint
        self.assertFalse(_match_training_request_to_person(request, tr, person, create))
        messages = request._messages._queued_messages  # type: ignore
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].level, WARNING)


class TestTrainingRequestTemplateTags(TestBase):
    def test_pending_request(self):
        self._test(state="p", expected="badge badge-warning")

    def test_accepted_request(self):
        self._test(state="a", expected="badge badge-success")

    def test_discarded_request(self):
        self._test(state="d", expected="badge badge-danger")

    def _test(self, state, expected):
        template = Template("{% load state %}" "{% state_label req %}")
        training_request = TrainingRequest(state=state)
        context = Context({"req": training_request})
        got = template.render(context)
        self.assertEqual(got, expected)


class TestTrainingRequestMerging(TestBase):
    # there's little need to check for extra corner cases
    # because they're covered by merging tests in `test_person`
    # and `test_event`

    def setUp(self):
        # self.clear_sites_cache()
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()
        self._setUpSites()

        self.first_req = create_training_request(state="d", person=self.spiderman)
        self.first_req.secondary_email = "notused@example.org"
        self.second_req = create_training_request(state="p", person=None)
        self.third_req = create_training_request(state="a", person=self.ironman)
        self.third_req.secondary_email = "notused@amy.org"

        # comments regarding first request
        self.ca = Comment.objects.create(
            content_object=self.first_req,
            user=self.spiderman,
            comment="Comment from admin on first_req",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )
        # comments regarding second request
        self.cb = Comment.objects.create(
            content_object=self.second_req,
            user=self.ironman,
            comment="Comment from admin on second_req",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )

        # assign roles (previous involvement with The Carpentries) and
        # knowledge domains - those are the hardest to merge successfully
        self.chemistry = KnowledgeDomain.objects.get(name="Chemistry")
        self.physics = KnowledgeDomain.objects.get(name="Physics")
        self.humanities = KnowledgeDomain.objects.get(name="Humanities")
        self.education = KnowledgeDomain.objects.get(name="Education")
        self.social = KnowledgeDomain.objects.get(name="Social sciences")
        self.first_req.domains.set([self.chemistry, self.physics])
        self.second_req.domains.set([self.humanities, self.social])
        self.third_req.domains.set([self.education])

        self.learner = Role.objects.get(name="learner")
        self.helper = Role.objects.get(name="helper")
        self.instructor = Role.objects.get(name="instructor")
        self.contributor = Role.objects.get(name="contributor")
        self.first_req.previous_involvement.set([self.learner])
        self.second_req.previous_involvement.set([self.helper])
        self.third_req.previous_involvement.set([self.instructor, self.contributor])

        # consents
        may_contact_term = Term.objects.get_by_key(TermEnum.MAY_CONTACT)
        privacy_policy_term = Term.objects.get_by_key(TermEnum.PRIVACY_POLICY)
        public_profile_term = Term.objects.get_by_key(TermEnum.PUBLIC_PROFILE)

        self.first_req_may_contact_consent = TrainingRequestConsent.objects.create(
            training_request=self.first_req,
            term=may_contact_term,
            term_option=TermOption.objects.filter(term=may_contact_term).get_decline_term_option(),
        )
        self.first_req_may_contact_consent.created_at = datetime(2023, 4, 10, tzinfo=timezone.utc)
        self.first_req_may_contact_consent.save()

        self.second_req_may_contact_consent = TrainingRequestConsent.objects.create(
            training_request=self.second_req,
            term=may_contact_term,
            term_option=TermOption.objects.filter(term=may_contact_term).get_decline_term_option(),
        )
        self.second_req_may_contact_consent.created_at = datetime(2023, 4, 11, tzinfo=timezone.utc)
        self.second_req_may_contact_consent.save()

        self.third_req_may_contact_consent = TrainingRequestConsent.objects.create(
            training_request=self.third_req,
            term=may_contact_term,
            term_option=TermOption.objects.filter(term=may_contact_term).get_agree_term_option(),
        )
        self.third_req_may_contact_consent.created_at = datetime(2023, 4, 12, tzinfo=timezone.utc)
        self.third_req_may_contact_consent.save()

        self.first_req_privacy_policy_consent = TrainingRequestConsent.objects.create(
            training_request=self.first_req,
            term=privacy_policy_term,
            term_option=TermOption.objects.filter(term=privacy_policy_term).get_agree_term_option(),
        )
        self.first_req_privacy_policy_consent.created_at = datetime(2023, 4, 12, tzinfo=timezone.utc)
        self.first_req_privacy_policy_consent.save()

        self.second_req_privacy_policy_consent = TrainingRequestConsent.objects.create(
            training_request=self.second_req,
            term=privacy_policy_term,
            term_option=TermOption.objects.filter(term=privacy_policy_term).get_agree_term_option(),
        )
        self.second_req_privacy_policy_consent.created_at = datetime(2023, 4, 11, tzinfo=timezone.utc)
        self.second_req_privacy_policy_consent.save()

        self.third_req_privacy_policy_consent = TrainingRequestConsent.objects.create(
            training_request=self.third_req,
            term=privacy_policy_term,
            term_option=TermOption.objects.filter(term=privacy_policy_term).get_agree_term_option(),
        )
        self.third_req_privacy_policy_consent.created_at = datetime(2023, 4, 10, tzinfo=timezone.utc)
        self.third_req_privacy_policy_consent.save()

        self.first_req_public_profile_consent = TrainingRequestConsent.objects.create(
            training_request=self.first_req,
            term=public_profile_term,
            term_option=TermOption.objects.filter(term=public_profile_term).get_decline_term_option(),
        )
        self.first_req_public_profile_consent.created_at = datetime(2023, 4, 11, tzinfo=timezone.utc)
        self.first_req_public_profile_consent.save()

        self.second_req_public_profile_consent = TrainingRequestConsent.objects.create(
            training_request=self.second_req,
            term=public_profile_term,
            term_option=TermOption.objects.filter(term=public_profile_term).get_agree_term_option(),
        )
        self.second_req_public_profile_consent.created_at = datetime(2023, 4, 10, tzinfo=timezone.utc)
        self.second_req_public_profile_consent.save()

        self.third_req_public_profile_consent = TrainingRequestConsent.objects.create(
            training_request=self.third_req,
            term=public_profile_term,
            term_option=TermOption.objects.filter(term=public_profile_term).get_decline_term_option(),
        )
        self.third_req_public_profile_consent.created_at = datetime(2023, 4, 12, tzinfo=timezone.utc)
        self.third_req_public_profile_consent.save()

        # prepare merge strategies (POST data to be sent to the merging view)
        self.strategy_1 = {
            "trainingrequest_a": self.first_req.pk,
            "trainingrequest_b": self.second_req.pk,
            "id": "obj_a",
            "state": "obj_b",
            "person": "obj_a",
            "member_code": "obj_a",
            "personal": "obj_a",
            "middle": "obj_a",
            "family": "obj_a",
            "email": "obj_a",
            "secondary_email": "obj_a",
            "github": "obj_a",
            "occupation": "obj_a",
            "occupation_other": "obj_a",
            "affiliation": "obj_a",
            "location": "obj_a",
            "country": "obj_a",
            "underresourced": "obj_a",
            "domains": "obj_a",
            "domains_other": "obj_a",
            "underrepresented": "obj_a",
            "underrepresented_details": "obj_a",
            "nonprofit_teaching_experience": "obj_a",
            "previous_involvement": "obj_b",
            "previous_training": "obj_a",
            "previous_training_other": "obj_a",
            "previous_training_explanation": "obj_a",
            "previous_experience": "obj_a",
            "previous_experience_other": "obj_a",
            "previous_experience_explanation": "obj_a",
            "programming_language_usage_frequency": "obj_a",
            "checkout_intent": "obj_a",
            "teaching_intent": "obj_a",
            "teaching_frequency_expectation": "obj_a",
            "teaching_frequency_expectation_other": "obj_a",
            "max_travelling_frequency": "obj_a",
            "max_travelling_frequency_other": "obj_a",
            "reason": "obj_a",
            "user_notes": "obj_a",
            "data_privacy_agreement": "obj_a",
            "code_of_conduct_agreement": "obj_a",
            "created_at": "obj_a",
            "comments": "combine",
            "trainingrequestconsent_set": "most_recent",
        }
        self.strategy_2 = {
            "trainingrequest_a": self.first_req.pk,
            "trainingrequest_b": self.third_req.pk,
            "id": "obj_b",
            "state": "obj_a",
            "person": "obj_a",
            "member_code": "obj_b",
            "personal": "obj_b",
            "middle": "obj_b",
            "family": "obj_b",
            "email": "obj_b",
            "secondary_email": "obj_b",
            "github": "obj_b",
            "occupation": "obj_b",
            "occupation_other": "obj_b",
            "affiliation": "obj_b",
            "location": "obj_b",
            "country": "obj_b",
            "underresourced": "obj_b",
            "domains": "combine",
            "domains_other": "obj_b",
            "underrepresented": "obj_b",
            "underrepresented_details": "obj_b",
            "nonprofit_teaching_experience": "obj_b",
            "previous_involvement": "combine",
            "previous_training": "obj_a",
            "previous_training_other": "obj_a",
            "previous_training_explanation": "obj_a",
            "previous_experience": "obj_a",
            "previous_experience_other": "obj_a",
            "previous_experience_explanation": "obj_a",
            "programming_language_usage_frequency": "obj_a",
            "checkout_intent": "obj_a",
            "teaching_intent": "obj_a",
            "teaching_frequency_expectation": "obj_a",
            "teaching_frequency_expectation_other": "obj_a",
            "max_travelling_frequency": "obj_a",
            "max_travelling_frequency_other": "obj_a",
            "reason": "obj_a",
            "user_notes": "obj_a",
            "data_privacy_agreement": "obj_a",
            "code_of_conduct_agreement": "obj_a",
            "created_at": "obj_a",
            "comments": "combine",
            "trainingrequestconsent_set": "most_recent",
        }

        base_url = reverse("trainingrequests_merge")
        query_1 = urlencode(
            {
                "trainingrequest_a": self.first_req.pk,
                "trainingrequest_b": self.second_req.pk,
            }
        )
        query_2 = urlencode(
            {
                "trainingrequest_a": self.first_req.pk,
                "trainingrequest_b": self.third_req.pk,
            }
        )
        self.url_1 = "{}?{}".format(base_url, query_1)
        self.url_2 = "{}?{}".format(base_url, query_2)

    def test_form_invalid_values(self):
        """Make sure only a few fields accept third option ("combine")."""
        hidden = {
            "trainingrequest_a": self.first_req.pk,
            "trainingrequest_b": self.second_req.pk,
        }
        # fields accepting only 2 options: "obj_a" and "obj_b"
        failing = {
            "id": "combine",
            "state": "combine",
            "person": "combine",
            "member_code": "combine",
            "personal": "combine",
            "middle": "combine",
            "family": "combine",
            "email": "combine",
            "secondary_email": "combine",
            "github": "combine",
            "occupation": "combine",
            "occupation_other": "combine",
            "affiliation": "combine",
            "location": "combine",
            "country": "combine",
            "underresourced": "combine",
            "domains_other": "combine",
            "underrepresented": "combine",
            "underrepresented_details": "combine",
            "nonprofit_teaching_experience": "combine",
            "previous_training": "combine",
            "previous_training_other": "combine",
            "previous_training_explanation": "combine",
            "previous_experience": "combine",
            "previous_experience_other": "combine",
            "previous_experience_explanation": "combine",
            "programming_language_usage_frequency": "combine",
            "checkout_intent": "combine",
            "teaching_intent": "combine",
            "teaching_frequency_expectation": "combine",
            "teaching_frequency_expectation_other": "combine",
            "max_travelling_frequency": "combine",
            "max_travelling_frequency_other": "combine",
            "data_privacy_agreement": "combine",
            "code_of_conduct_agreement": "combine",
            "created_at": "combine",
            # it actually accepts only "most_recent"
            "trainingrequestconsent_set": "combine",
        }
        # fields additionally accepting "combine"
        passing = {
            "domains": "combine",
            "previous_involvement": "combine",
            "reason": "combine",
            "user_notes": "combine",
            "comments": "combine",
        }
        data = hidden.copy()
        data.update(failing)
        data.update(passing)

        form = TrainingRequestsMergeForm(data)
        self.assertFalse(form.is_valid())

        self.assertEqual(form.errors.keys(), failing.keys())  # the same keys
        self.assertTrue(form.errors.keys().isdisjoint(passing.keys()))  # no overlap

        # make sure no fields are added without this test being updated
        self.assertEqual(set(list(form.fields.keys())), set(list(data.keys())))

    def test_merging_base_trainingrequest(self):
        """Merging: ensure the base training request is selected based on ID
        form field.

        If ID field has a value of 'obj_b', then 1st training req is base and
        it won't be removed from the database after the merge. 2nd training
        req, on the other hand, will."""
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)

        self.first_req.refresh_from_db()
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.second_req.refresh_from_db()

    def test_merging_basic_attributes(self):
        """Merging: ensure basic (non-relationships) attributes are properly
        saved."""
        assertions = {
            "id": self.first_req.id,
            "state": self.second_req.state,
            "person": self.first_req.person,
            "member_code": self.first_req.member_code,
            "personal": self.first_req.personal,
            "middle": self.first_req.middle,
            "family": self.first_req.family,
            "email": self.first_req.email,
            "github": self.first_req.github,
            "occupation": self.first_req.occupation,
            "occupation_other": self.first_req.occupation_other,
            "affiliation": self.first_req.affiliation,
            "location": self.first_req.location,
            "country": self.first_req.country,
            "underresourced": self.first_req.underresourced,
            "domains_other": self.first_req.domains_other,
            "underrepresented": self.first_req.underrepresented,
            "nonprofit_teaching_experience": self.first_req.nonprofit_teaching_experience,  # noqa: line too long
            "previous_training": self.first_req.previous_training,
            "previous_training_other": self.first_req.previous_training_other,
            "previous_training_explanation": self.first_req.previous_training_explanation,  # noqa: line too long
            "previous_experience": self.first_req.previous_experience,
            "previous_experience_other": self.first_req.previous_experience_other,
            "previous_experience_explanation": self.first_req.previous_experience_explanation,  # noqa: line too long
            "programming_language_usage_frequency": self.first_req.programming_language_usage_frequency,  # noqa: line too long
            "checkout_intent": self.first_req.checkout_intent,
            "teaching_intent": self.first_req.teaching_intent,
            "teaching_frequency_expectation": self.first_req.teaching_frequency_expectation,  # noqa: line too long
            "teaching_frequency_expectation_other": self.first_req.teaching_frequency_expectation_other,  # noqa: line too long
            "max_travelling_frequency": self.first_req.max_travelling_frequency,
            "max_travelling_frequency_other": self.first_req.max_travelling_frequency_other,  # noqa: line too long
            "reason": self.first_req.reason,
            "user_notes": self.first_req.user_notes,
            "data_privacy_agreement": self.first_req.data_privacy_agreement,
            "code_of_conduct_agreement": self.first_req.code_of_conduct_agreement,
            "created_at": self.first_req.created_at,
        }
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(getattr(self.first_req, key), value, key)

    def test_merging_relational_attributes(self):
        """Merging: ensure relational fields are properly saved/combined."""
        assertions = {
            "domains": set([self.chemistry, self.physics]),
            "previous_involvement": set([self.helper]),
            # comments are not relational, they're related via generic FKs,
            # so they won't appear here
        }

        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(set(getattr(self.first_req, key).all()), value, key)

    def test_merging(self):
        rv = self.client.post(self.url_1, self.strategy_1, follow=True)
        self.assertEqual(rv.status_code, 200)
        # after successful merge, we should end up redirected to the details
        # page of the base object
        self.assertEqual(rv.resolver_match.view_name, "trainingrequest_details")

        # check if objects merged
        self.first_req.refresh_from_db()
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.second_req.refresh_from_db()
        self.third_req.refresh_from_db()

        # try second strategy
        rv = self.client.post(self.url_2, self.strategy_2, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "trainingrequest_details")

        # check if objects merged
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.first_req.refresh_from_db()
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.second_req.refresh_from_db()
        self.third_req.refresh_from_db()

        # check if third request properties changed accordingly
        self.assertEqual(self.third_req.personal, "John")
        self.assertEqual(self.third_req.family, "Smith")
        self.assertEqual(self.third_req.state, "p")
        self.assertEqual(self.third_req.person, self.spiderman)
        domains_set = set([self.chemistry, self.physics, self.education])
        roles_set = set([self.helper, self.instructor, self.contributor])
        self.assertEqual(domains_set, set(self.third_req.domains.all()))
        self.assertEqual(roles_set, set(self.third_req.previous_involvement.all()))
        self.assertEqual(self.third_req.trainingrequestconsent_set.active().count(), 3)

        # make sure no M2M related objects were removed from DB
        self.chemistry.refresh_from_db()
        self.physics.refresh_from_db()
        self.humanities.refresh_from_db()
        self.education.refresh_from_db()
        self.social.refresh_from_db()

        self.learner.refresh_from_db()
        self.helper.refresh_from_db()
        self.instructor.refresh_from_db()
        self.contributor.refresh_from_db()

        # make sure no related persons were removed from DB
        self.ironman.refresh_from_db()
        self.spiderman.refresh_from_db()

    def test_merging_comments_strategy1(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 1 (combine)."""
        self.strategy_1["comments"] = "combine"
        comments = [self.ca, self.cb]
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.first_req).filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy2(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 2 (object a)."""
        self.strategy_1["comments"] = "obj_a"
        comments = [self.ca]
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.first_req).filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy3(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 3 (object b)."""
        self.strategy_1["comments"] = "obj_b"
        comments = [self.cb]
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.first_req).filter(is_removed=False)),
            set(comments),
        )

    def test_merging_consents_most_recent(self):
        """Ensure consents regarding persons are correctly merged using
        `merge_objects`.
        This test uses "most_recent" strategy."""
        # Arrange
        self.strategy_1["trainingrequestconsent_set"] = "most_recent"
        self.strategy_2["trainingrequestconsent_set"] = "most_recent"

        # Act
        rv_1 = self.client.post(self.url_1, data=self.strategy_1)
        rv_2 = self.client.post(self.url_2, data=self.strategy_2)

        # Assert
        self.assertEqual(rv_1.status_code, 302)
        self.assertEqual(rv_2.status_code, 302)

        # There are exactly 3 active (non-archived) consents
        self.assertEqual(
            len(TrainingRequestConsent.objects.active().filter(training_request=self.third_req)),
            3,
        )
        with self.assertRaises(TrainingRequestConsent.DoesNotExist):
            self.first_req_may_contact_consent.refresh_from_db()
        with self.assertRaises(TrainingRequestConsent.DoesNotExist):
            self.second_req_may_contact_consent.refresh_from_db()
        with self.assertRaises(TrainingRequestConsent.DoesNotExist):
            self.second_req_privacy_policy_consent.refresh_from_db()
        with self.assertRaises(TrainingRequestConsent.DoesNotExist):
            self.first_req_public_profile_consent.refresh_from_db()
        with self.assertRaises(TrainingRequestConsent.DoesNotExist):
            self.second_req_public_profile_consent.refresh_from_db()

        # There are 4 remaining consents, and one is archived
        self.third_req_may_contact_consent.refresh_from_db()
        self.first_req_privacy_policy_consent.refresh_from_db()
        self.third_req_privacy_policy_consent.refresh_from_db()
        self.third_req_public_profile_consent.refresh_from_db()
        self.assertNotEqual(self.third_req_privacy_policy_consent.archived_at, None)

        # No consents linked to old requests
        self.third_req.refresh_from_db()
        self.assertEqual(
            len(TrainingRequestConsent.objects.filter(training_request__in=[self.first_req, self.second_req])),
            0,
        )
