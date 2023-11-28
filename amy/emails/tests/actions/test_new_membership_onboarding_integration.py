from datetime import date, timedelta
from unittest.mock import patch

from django.test import RequestFactory, override_settings
from django.urls import reverse

from emails.actions.new_membership_onboarding import (
    new_membership_onboarding_strategy,
    run_new_membership_onboarding_strategy,
)
from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from emails.signals import NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME
from fiscal.models import MembershipPersonRole, MembershipTask
from workshops.models import Member, MemberRole, Membership
from workshops.tests.base import TestBase


class TestNewMembershipOnboardingReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
            variant="partner",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )
        billing_contact_role = MembershipPersonRole.objects.create(
            name="billing_contact"
        )
        # task = MembershipTask.objects.create(
        #     person=self.hermione,
        #     membership=membership,
        #     role=billing_contact_role,
        # )

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        url = reverse("membership_tasks", args=[membership.pk])
        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": membership.pk,
            "form-0-person": self.hermione.pk,
            "form-0-role": billing_contact_role.pk,
            "form-0-id": "",
            "form-0-EDITABLE": True,
        }

        # Act
        rv = self.client.post(url, data=data)

        # Arrange
        self.assertEqual(rv.status_code, 302)
        scheduled_email = ScheduledEmail.objects.get(template=template)
        self.assertEqual(scheduled_email.to_header, [self.hermione.email])


class TestNewMembershipOnboardingUpdateReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
            name="Test Membership",
            variant="partner",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )
        billing_contact_role = MembershipPersonRole.objects.create(
            name="billing_contact"
        )
        MembershipTask.objects.create(
            person=self.hermione,
            membership=membership,
            role=billing_contact_role,
        )

        signal = NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        with patch(
            "emails.actions.base_action.messages_action_scheduled"
        ) as mock_action_scheduled:
            run_new_membership_onboarding_strategy(
                new_membership_onboarding_strategy(membership),
                request=request,
                membership=membership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("membership_edit", args=[membership.pk])
        data = {
            "name": membership.name,
            "public_status": membership.public_status,
            "variant": membership.variant,
            "agreement_start": membership.agreement_start,
            "agreement_end": membership.agreement_end,
            "contribution_type": membership.contribution_type,
            "public_instructor_training_seats": 1,
            "additional_public_instructor_training_seats": 2,
            "inhouse_instructor_training_seats": 3,
            "additional_inhouse_instructor_training_seats": 4,
            "workshops_without_admin_fee_rolled_from_previous": 5,
            "public_instructor_training_seats_rolled_over": 6,
            "inhouse_instructor_training_seats_rolled_over": 7,
        }

        # Act
        rv = self.client.post(url, data=data)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        latest_log = (
            ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email)
            .order_by("-created_at")
            .first()
        )
        assert latest_log
        self.assertEqual(latest_log.details, f"Updated {signal}")


class TestNewMembershipOnboardingRemoveReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
            name="Test Membership",
            variant="partner",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        member = Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )
        billing_contact_role = MembershipPersonRole.objects.create(
            name="billing_contact"
        )
        task = MembershipTask.objects.create(
            person=self.hermione,
            membership=membership,
            role=billing_contact_role,
        )

        signal = NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        with patch(
            "emails.actions.base_action.messages_action_scheduled"
        ) as mock_action_scheduled:
            run_new_membership_onboarding_strategy(
                new_membership_onboarding_strategy(membership),
                request=request,
                membership=membership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("membership_delete", args=[membership.pk])

        # Act
        # need to first delete the membership task and the member
        task.delete()
        member.delete()
        rv = self.client.post(url)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        latest_log = (
            ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email)
            .order_by("-created_at")
            .first()
        )
        assert latest_log
        self.assertEqual(latest_log.details, "Email was cancelled")

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration__not_removed_because_of_related_objects(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
            name="Test Membership",
            variant="partner",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )
        billing_contact_role = MembershipPersonRole.objects.create(
            name="billing_contact"
        )
        MembershipTask.objects.create(
            person=self.hermione,
            membership=membership,
            role=billing_contact_role,
        )

        signal = NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        with patch(
            "emails.actions.base_action.messages_action_scheduled"
        ) as mock_action_scheduled:
            run_new_membership_onboarding_strategy(
                new_membership_onboarding_strategy(membership),
                request=request,
                membership=membership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("membership_delete", args=[membership.pk])

        # Act
        rv = self.client.post(url)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 200)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        self.assertIn(
            "Not attempting to remove related scheduled emails, because there are "
            "still related objects in the database.",
            rv.content.decode("utf-8"),
        )
