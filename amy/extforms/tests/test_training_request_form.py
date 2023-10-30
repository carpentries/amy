from datetime import date, timedelta

from django.core import mail
from django.forms import CheckboxInput, HiddenInput
from django.test import override_settings
from django.urls import reverse

from consents.models import Term, TermOptionChoices
from extforms.views import TrainingRequestCreate
from workshops.models import Event, Membership, Role, Tag, Task, TrainingRequest
from workshops.tests.base import TestBase


class TestTrainingRequestForm(TestBase):
    INVALID_MEMBER_CODE_ERROR = "This code is invalid."
    MEMBER_CODE_OVERRIDE_EMAIL_TEXT = (
        "Continue with registration code marked as invalid"
    )

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self.data = {
            "review_process": "preapproved",
            "member_code": "coolprogrammers",
            "personal": "John",
            "family": "Smith",
            "email": "john@smith.com",
            "github": "",
            "occupation": "",
            "occupation_other": "unemployed",
            "affiliation": "AGH University of Science and Technology",
            "location": "Cracow",
            "country": "PL",
            "domains": [1, 2],
            "domains_other": "",
            "underrepresented": "undisclosed",
            "previous_involvement": [Role.objects.get(name="host").id],
            "previous_training": "none",
            "previous_training_other": "",
            "previous_training_explanation": "",
            "previous_experience": "none",
            "previous_experience_other": "",
            "previous_experience_explanation": "",
            "programming_language_usage_frequency": "daily",
            "reason": "Just for fun.",
            "teaching_frequency_expectation": "monthly",
            "teaching_frequency_expectation_other": "",
            "max_travelling_frequency": "yearly",
            "max_travelling_frequency_other": "",
            "addition_skills": "",
            "user_notes": "",
            "agreed_to_code_of_conduct": "on",
            "agreed_to_complete_training": "on",
            "agreed_to_teach_workshops": "on",
            "privacy_consent": True,
        }
        self.data.update(self.add_terms_to_payload())

    def setUpMembership(self):
        self.membership = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date.today() - timedelta(weeks=26),
            agreement_end=date.today() + timedelta(weeks=26),
            contribution_type="financial",
            registration_code="valid123",
            public_instructor_training_seats=1,
            inhouse_instructor_training_seats=1,
        )

    def setUpUsedSeats(self):
        # set up some prior seat usage
        super().setUp()
        self._setUpTags()
        ttt_event = Event.objects.create(slug="ttt-event", host=self.org_alpha)
        ttt_event.tags.add(Tag.objects.get(name="TTT"))
        learner = Role.objects.get(name="learner")
        self.task_public = Task.objects.create(
            event=ttt_event,
            person=self.spiderman,
            role=learner,
            seat_membership=self.membership,
            seat_public=True,
        )
        self.task_inhouse = Task.objects.create(
            event=ttt_event,
            person=self.blackwidow,
            role=learner,
            seat_membership=self.membership,
            seat_public=False,
        )

    def add_terms_to_payload(self) -> dict[str, int]:
        data = {}
        terms = (
            Term.objects.prefetch_active_options()
            .filter(required_type=Term.PROFILE_REQUIRE_TYPE)
            .order_by("slug")
        )
        for term in terms:
            option = next(
                option
                for option in term.options
                if option.option_type == TermOptionChoices.AGREE
            )
            data[term.slug] = option.pk
        return data

    def test_request_added(self):
        # Arrange
        email = self.data.get("email")
        self.passCaptcha(self.data)

        # Act
        rv = self.client.post(reverse("training_request"), self.data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, "fix errors in the form below")
        self.assertEqual(TrainingRequest.objects.all().count(), 1)

        # Test that the sender was emailed
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [email])
        self.assertEqual(msg.subject, TrainingRequestCreate.autoresponder_subject)
        self.assertIn("A copy of your request", msg.body)
        self.assertNotIn(self.MEMBER_CODE_OVERRIDE_EMAIL_TEXT, msg.body)

    def test_invalid_request_not_added(self):
        # Arrange
        self.data.pop("personal")  # remove a required field
        self.passCaptcha(self.data)

        # Act
        rv = self.client.post(reverse("training_request"), self.data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, "fix errors in the form below")
        self.assertEqual(TrainingRequest.objects.all().count(), 0)

        # Test that the sender was not emailed
        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(TrainingRequest.objects.all().count(), 0)

    def test_review_process_validation__preapproved_code_empty(self):
        """Shouldn't pass when review_process requires member_code."""
        # Arrange
        data = {
            "review_process": "preapproved",
            "member_code": "",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(
            rv,
            "Registration code is required for pre-approved training review process.",
        )
        # test that override field is not visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            HiddenInput,
        )

    def test_review_process_validation__open_code_nonempty(self):
        """Shouldn't pass when review_process requires *NO* member_code."""
        # Arrange
        data = {
            "review_process": "open",
            "member_code": "some_code",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(
            rv, "Registration code must be empty for open training review process."
        )
        # test that override field is not visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            HiddenInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", False)]})
    def test_member_code_validation__not_enforced(self):
        """Invalid code should pass if enforcement is not enabled."""
        # Arrange
        data = {
            "review_process": "preapproved",
            "member_code": "invalid",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_valid(self):
        """Valid member code should pass."""
        # Arrange
        self.setUpMembership()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)
        # test that override field is not visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            HiddenInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_invalid(self):
        """Invalid member code should not pass."""
        # Arrange
        data = {
            "review_process": "preapproved",
            "member_code": "invalid",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, self.INVALID_MEMBER_CODE_ERROR)
        # test that override field is visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            CheckboxInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_inactive_early(self):
        """Code used >90 days before membership start date should not pass."""
        # Arrange
        self.setUpMembership()
        self.membership.agreement_start = date.today() + timedelta(days=91)
        self.membership.save()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, self.INVALID_MEMBER_CODE_ERROR)
        # test that override field is visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            CheckboxInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_inactive_late(self):
        """Code used >90 days after membership end date should not pass."""
        # Arrange
        self.setUpMembership()
        self.membership.agreement_end = date.today() - timedelta(days=91)
        self.membership.save()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, self.INVALID_MEMBER_CODE_ERROR)
        # test that override field is visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            CheckboxInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_no_seats_remaining(self):
        """Code with no seats remaining should not pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, self.INVALID_MEMBER_CODE_ERROR)
        # test that override field is visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            CheckboxInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_only_public_seats_remaining(self):
        """Code with only public seats remaining should pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        self.task_public.delete()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_only_inhouse_seats_remaining(self):
        """Code with only inhouse seats remaining should pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        self.task_inhouse.delete()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_invalid_override(self):
        """Invalid member code should be accepted when the override is ticked."""
        # Arrange
        data = {
            "review_process": "preapproved",
            "member_code": "invalid",
            "member_code_override": True,
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)
        # test that override field is visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            CheckboxInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_valid_override(self):
        """Override should be quietly hidden if a valid code is used."""
        # Arrange
        self.setUpMembership()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
            "member_code_override": True,
        }

        # Act
        rv = self.client.post(reverse("training_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)
        # test that override field is not visible
        self.assertEqual(
            rv.context["form"].fields["member_code_override"].widget.__class__,
            HiddenInput,
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_valid_override_full_request(self):
        """Override should be quietly changed to False if a valid code is used
        in a successful submission."""
        # Arrange
        self.setUpMembership()
        self.data["member_code"] = "valid123"
        self.data["member_code_override"] = True
        self.passCaptcha(self.data)

        # Act
        rv = self.client.post(reverse("training_request"), data=self.data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training_request_confirm")
        self.assertFalse(
            TrainingRequest.objects.get(member_code="valid123").member_code_override
        )

        # Test that the sender was emailed with correct content
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertNotIn(self.MEMBER_CODE_OVERRIDE_EMAIL_TEXT, msg.body)

    def test_member_code_validation__code_invalid_override_full_request(self):
        """Sent email should include the member_code_override field if used."""
        # Arrange
        self.setUpMembership()
        self.data["member_code"] = "invalid"
        self.data["member_code_override"] = True
        self.passCaptcha(self.data)

        # Act
        rv = self.client.post(reverse("training_request"), data=self.data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training_request_confirm")
        self.assertTrue(
            TrainingRequest.objects.get(member_code="invalid").member_code_override
        )

        # Test that the sender was emailed with correct content
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn(self.MEMBER_CODE_OVERRIDE_EMAIL_TEXT, msg.body)
