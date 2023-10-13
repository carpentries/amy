from datetime import date, timedelta

from django.core import mail
from django.test import override_settings
from django.urls import reverse

from consents.models import Term, TermOptionChoices
from extforms.views import TrainingRequestCreate
from workshops.models import Membership, Role, TrainingRequest
from workshops.tests.base import TestBase


class TestTrainingRequestForm(TestBase):
    INVALID_MEMBER_CODE_ERROR = (
        "This code is invalid. "
        "Please contact your Member Affiliate to verify your code."
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
        Membership.objects.create(
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
        email = "john@smith.com"
        self.passCaptcha(self.data)

        rv = self.client.post(reverse("training_request"), self.data, follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode("utf-8")
        self.assertNotIn("fix errors in the form below", content)
        self.assertEqual(TrainingRequest.objects.all().count(), 1)

        # Test that the sender was emailed
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [email])
        self.assertEqual(msg.subject, TrainingRequestCreate.autoresponder_subject)
        self.assertIn("A copy of your request", msg.body)
        # with open('email.eml', 'wb') as f:
        #     f.write(msg.message().as_bytes())

    def test_review_process_validation__preapproved_code_empty(self):
        # 1: shouldn't pass when review_process requires member_code
        self.data["review_process"] = "preapproved"
        self.data["member_code"] = ""
        self.passCaptcha(self.data)

        rv = self.client.post(reverse("training_request"), self.data, follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode("utf-8")
        self.assertIn("fix errors in the form below", content)
        self.assertEqual(TrainingRequest.objects.all().count(), 0)

    def test_review_process_validation__open_code_nonempty(self):
        # 2: shouldn't pass when review_process requires *NO* member_code
        self.data["review_process"] = "open"
        self.data["member_code"] = "some_code"
        self.passCaptcha(self.data)

        rv = self.client.post(reverse("training_request"), self.data, follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode("utf-8")
        self.assertIn("fix errors in the form below", content)
        self.assertEqual(TrainingRequest.objects.all().count(), 0)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_valid(self):
        # 1: valid code - no error
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
        # 2: invalid code - error on code
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
