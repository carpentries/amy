from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse

from src.extrequests.forms import BulkMatchTrainingRequestForm
from src.extrequests.tests.test_training_request import create_training_request
from src.offering.models import Account, AccountBenefit, Benefit
from src.workshops.models import (
    Event,
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
from src.workshops.tests.base import TestBase


class TestTrainingRequestUpdateForm(TestBase):
    INVALID_MEMBER_CODE_ERROR = "This code is invalid."

    def setUp(self) -> None:
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self.request = create_training_request(state="p", person=None, open_review=False)

    def setUpMembership(self) -> None:
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

    def setUpUsedSeats(self) -> None:
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

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", False)]})
    def test_member_code_validation__not_enforced(self) -> None:
        """Invalid code should pass if enforcement is not enabled."""
        # Arrange
        data = {
            "review_process": "preapproved",
            "member_code": "invalid",
        }

        # Act
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_valid(self) -> None:
        """Valid member code should pass."""
        # Arrange
        self.setUpMembership()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_invalid(self) -> None:
        """Invalid member code should not pass."""
        # Arrange
        data = {
            "review_process": "preapproved",
            "member_code": "invalid",
        }

        # Act
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, "No membership found for code &quot;invalid&quot;.")

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_inactive_early(self) -> None:
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
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(
            rv,
            f"Membership is inactive (start {self.membership.agreement_start}, end {self.membership.agreement_end}).",
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_inactive_late(self) -> None:
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
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(
            rv,
            f"Membership is inactive (start {self.membership.agreement_start}, end {self.membership.agreement_end}).",
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_no_seats_remaining(self) -> None:
        """Code with no seats remaining should not pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, "Membership has no training seats remaining.")

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_only_public_seats_remaining(self) -> None:
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
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_only_inhouse_seats_remaining(self) -> None:
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
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_invalid_override(self) -> None:
        """Invalid member code should be accepted when the override is ticked."""
        # Arrange
        data = {
            "review_process": "preapproved",
            "member_code": "invalid",
            "member_code_override": True,
        }

        # Act
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_valid_override(self) -> None:
        """Override should be quietly hidden if a valid code is used."""
        # Arrange
        self.setUpMembership()
        data = {
            "review_process": "preapproved",
            "member_code": "valid123",
            "member_code_override": True,
        }

        # Act
        rv = self.client.post(reverse("trainingrequest_edit", args=[self.request.pk]), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_MEMBER_CODE_ERROR)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__code_valid_override_full_request(self) -> None:
        """Override should be quietly changed to False if a valid code is used
        in a successful submission."""
        # Arrange
        super().setUp()
        self.setUpMembership()
        data = self.request.__dict__
        data["person_id"] = self.spiderman.pk
        data["member_code"] = "valid123"
        data["member_code_override"] = True
        data.pop("score_manual")  # can't encode None in POST request, so omit

        # Act
        rv = self.client.post(
            reverse("trainingrequest_edit", args=[self.request.pk]),
            data=data,
            follow=True,
        )

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "trainingrequest_details")
        self.assertFalse(TrainingRequest.objects.get(member_code="valid123").member_code_override)


class TestBulkMatchTrainingRequestForm(TestCase):
    def test_clean__valid_data__no_membership_no_benefit(self) -> None:
        """Test that form is valid with correct data."""
        # Arrange
        person = Person.objects.create(username="test")
        training_request = create_training_request(state="p", person=person)
        organisation = Organization.objects.create(fullname="Test Org", domain="test.org")
        event = Event.objects.create(slug="test-event", host=organisation)
        event.tags.create(name="TTT")

        data = {
            "requests": [training_request.pk],
            "event": event.pk,
        }

        # Act
        form = BulkMatchTrainingRequestForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__valid_data__membership(self) -> None:
        """Test that form is valid with correct data."""
        # Arrange
        person = Person.objects.create(username="test")
        training_request = create_training_request(state="p", person=person)
        organisation = Organization.objects.create(fullname="Test Org", domain="test.org")
        event = Event.objects.create(slug="test-event", host=organisation)
        event.tags.create(name="TTT")
        membership = Membership.objects.create(
            name="alpha-name",
            variant="partner",
            registration_code="test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
        )
        Member.objects.create(
            membership=membership,
            organization=organisation,
            role=MemberRole.objects.all()[0],
        )

        data = {
            "requests": [training_request.pk],
            "event": event.pk,
            "seat_membership": membership.pk,
        }

        # Act
        form = BulkMatchTrainingRequestForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__valid_data__auto_assign_membership(self) -> None:
        """Test that form is valid with correct data."""
        # Arrange
        person = Person.objects.create(username="test")
        training_request = create_training_request(state="p", person=person, reg_code="test")
        organisation = Organization.objects.create(fullname="Test Org", domain="test.org")
        event = Event.objects.create(slug="test-event", host=organisation)
        event.tags.create(name="TTT")
        membership = Membership.objects.create(
            name="alpha-name",
            variant="partner",
            registration_code="test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
        )
        Member.objects.create(
            membership=membership,
            organization=organisation,
            role=MemberRole.objects.all()[0],
        )

        data = {
            "requests": [training_request.pk],
            "event": event.pk,
            "seat_membership_auto_assign": True,
        }

        # Act
        form = BulkMatchTrainingRequestForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__valid_data__benefit(self) -> None:
        """Test that form is valid with correct data."""
        # Arrange
        person = Person.objects.create(username="test")
        training_request = create_training_request(state="p", person=person)
        organisation = Organization.objects.create(fullname="Test Org", domain="test.org")
        event = Event.objects.create(slug="test-event", host=organisation)
        event.tags.create(name="TTT")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        benefit = Benefit.objects.create(
            name="Test Benefit",
            unit_type="seat",
            credits=2,
        )
        account_benefit = AccountBenefit.objects.create(
            account=account,
            benefit=benefit,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=365),
            allocation=2,
        )

        data = {
            "requests": [training_request.pk],
            "event": event.pk,
            "allocated_benefit": account_benefit.pk,
        }

        # Act
        form = BulkMatchTrainingRequestForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__unmatched_trainees(self) -> None:
        """Test that form is invalid when there are unmatched trainees."""
        # Arrange
        training_request = create_training_request(state="p", person=None)
        organisation = Organization.objects.create(fullname="Test Org", domain="test.org")
        event = Event.objects.create(slug="test-event", host=organisation)
        event.tags.create(name="TTT")
        data = {
            "requests": [training_request.pk],
            "event": event.pk,
        }

        # Act
        form = BulkMatchTrainingRequestForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        msg = (
            "Some of the requests are not matched to a trainee yet. Before matching them to a training, you "
            "need to accept them and match with a trainee."
        )
        self.assertIn(msg, form.errors["__all__"])

    def test_clean__membership_with_autoassign(self) -> None:
        """Test that form is invalid when membership has auto-assign enabled."""
        # Arrange
        person = Person.objects.create(username="test")
        training_request = create_training_request(state="p", person=person)
        organisation = Organization.objects.create(fullname="Test Org", domain="test.org")
        event = Event.objects.create(slug="test-event", host=organisation)
        event.tags.create(name="TTT")
        membership = Membership.objects.create(
            name="alpha-name",
            variant="partner",
            registration_code="test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
        )
        Member.objects.create(
            membership=membership,
            organization=organisation,
            role=MemberRole.objects.all()[0],
        )
        data = {
            "requests": [training_request.pk],
            "event": event.pk,
            "seat_membership": membership.pk,
            "seat_membership_auto_assign": True,
        }

        # Act
        form = BulkMatchTrainingRequestForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        msg = (
            "Cannot simultaneously use seats from selected membership and auto-assign seats based on registration code."
        )
        self.assertIn(msg, form.errors["seat_membership_auto_assign"])

    def test_clean__benefit_with_membership_or_auto_assign(self) -> None:
        """Test that form is invalid when benefit is used with membership or auto-assign."""
        # Arrange
        person = Person.objects.create(username="test")
        training_request = create_training_request(state="p", person=person)
        organisation = Organization.objects.create(fullname="Test Org", domain="test.org")
        event = Event.objects.create(slug="test-event", host=organisation)
        event.tags.create(name="TTT")
        membership = Membership.objects.create(
            name="alpha-name",
            variant="partner",
            registration_code="test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
        )
        Member.objects.create(
            membership=membership,
            organization=organisation,
            role=MemberRole.objects.all()[0],
        )
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        benefit = Benefit.objects.create(
            name="Test Benefit",
            unit_type="seat",
            credits=2,
        )
        account_benefit = AccountBenefit.objects.create(
            account=account,
            benefit=benefit,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=365),
            allocation=2,
        )
        data1 = {
            "requests": [training_request.pk],
            "event": event.pk,
            "seat_membership": membership.pk,
            "allocated_benefit": account_benefit.pk,
        }
        data2 = {
            "requests": [training_request.pk],
            "event": event.pk,
            "seat_membership_auto_assign": True,
            "allocated_benefit": account_benefit.pk,
        }

        # Act
        form1 = BulkMatchTrainingRequestForm(data1)
        form2 = BulkMatchTrainingRequestForm(data2)

        # Assert
        msg = (
            "Cannot simultaneously use an explicitly selected benefit and "
            "use seats from membership or auto-assign membership."
        )

        self.assertFalse(form1.is_valid())
        self.assertIn(msg, form1.errors["allocated_benefit"])

        self.assertFalse(form2.is_valid())
        self.assertIn(msg, form2.errors["allocated_benefit"])
