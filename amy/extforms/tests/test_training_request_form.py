from datetime import date, timedelta

from django.core import mail
from django.test import override_settings
from django.urls import reverse

from consents.models import Term, TermOptionChoices
from extforms.views import TrainingRequestCreate
from workshops.models import Membership, Role, TrainingRequest
from workshops.tests.base import TestBase


class TestTrainingRequestForm(TestBase):
    INVALID_MEMBER_CODE_ERROR = "This code is invalid."

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
