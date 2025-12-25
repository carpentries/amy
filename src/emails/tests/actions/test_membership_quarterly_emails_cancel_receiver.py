from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, call, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from src.emails.actions.membership_quarterly_emails import (
    membership_quarterly_9_months_cancel_receiver,
    membership_quarterly_email_strategy,
    run_membership_quarterly_email_strategy,
)
from src.emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from src.emails.signals import (
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
    membership_quarterly_9_months_cancel_signal,
)
from src.fiscal.models import MembershipPersonRole, MembershipTask
from src.workshops.models import Membership, Person
from src.workshops.tests.base import TestBase


class TestInstructorTaskCreatedForWorkshopCancelReceiver(TestCase):
    def setUp(self) -> None:
        self.person = Person.objects.create(email="test@example.org")
        self.membership = Membership.objects.create(
            variant="gold",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        self.billing_contact_role = MembershipPersonRole.objects.create(name="billing_contact")
        self.membership_task = MembershipTask.objects.create(
            person=self.person,
            membership=self.membership,
            role=self.billing_contact_role,
        )

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    @patch("src.emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            membership_quarterly_9_months_cancel_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping membership_quarterly_9_months_cancel"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = membership_quarterly_9_months_cancel_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        membership_quarterly_9_months_cancel_signal.connect(membership_quarterly_9_months_cancel_receiver)
        new_receivers = membership_quarterly_9_months_cancel_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        request = RequestFactory().get("/")

        template = self.setUpEmailTemplate()
        scheduled_email = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )

        # Act
        with patch("src.emails.actions.base_action.messages_action_cancelled") as mock_messages_action_cancelled:
            membership_quarterly_9_months_cancel_signal.send(
                sender=self.membership,
                request=request,
                membership=self.membership,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_cancelled.assert_called_once_with(
            request,
            MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_action_cancelled")
    def test_email_cancelled(
        self,
        mock_messages_action_cancelled: MagicMock,
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        scheduled_email = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )

        # Act
        with patch("src.emails.actions.base_action.EmailController.cancel_email") as mock_cancel_email:
            membership_quarterly_9_months_cancel_signal.send(
                sender=self.membership,
                request=request,
                membership=self.membership,
            )

        # Assert
        mock_cancel_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_action_cancelled")
    def test_multiple_emails_cancelled(
        self,
        mock_messages_action_cancelled: MagicMock,
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        scheduled_email1 = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )
        scheduled_email2 = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )

        # Act
        with patch("src.emails.actions.base_action.EmailController.cancel_email") as mock_cancel_email:
            membership_quarterly_9_months_cancel_signal.send(
                sender=self.membership,
                request=request,
                membership=self.membership,
            )

        # Assert
        mock_cancel_email.assert_has_calls(
            [
                call(
                    scheduled_email=scheduled_email1,
                    author=None,
                ),
                call(
                    scheduled_email=scheduled_email2,
                    author=None,
                ),
            ]
        )


class TestInstructorTaskCreatedForWorkshopCancelIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
            name="Test Membership",
            consortium=False,
            variant="gold",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        billing_contact_role = MembershipPersonRole.objects.create(name="billing_contact")
        task = MembershipTask.objects.create(
            person=self.hermione,
            membership=membership,
            role=billing_contact_role,
        )

        signal = MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME
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
        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_membership_quarterly_email_strategy(
                signal,
                membership_quarterly_email_strategy(signal, membership),
                request,
                membership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("membership_delete", args=[membership.pk])

        # Act
        # need to first delete the membership task
        task.delete()
        rv = self.client.post(url)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, "Email was cancelled")

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration_when_removing_membership_task(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        billing_contact_role = MembershipPersonRole.objects.create(name="billing_contact")
        task = MembershipTask.objects.create(
            person=self.hermione,
            membership=membership,
            role=billing_contact_role,
        )

        signal = MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME
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

        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_membership_quarterly_email_strategy(
                signal,
                membership_quarterly_email_strategy(signal, membership),
                request,
                membership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("membership_tasks", args=[membership.pk])

        # Act
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-membership": membership.pk,
            "form-0-person": task.person.pk,
            "form-0-role": task.role.pk,
            "form-0-id": task.pk,
            "form-0-DELETE": "on",
        }
        rv = self.client.post(url, data=data)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(MembershipTask.objects.filter(membership=membership).count(), 0)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, "Email was cancelled")

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration__not_removed_because_of_related_objects(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        billing_contact_role = MembershipPersonRole.objects.create(name="billing_contact")
        MembershipTask.objects.create(
            person=self.hermione,
            membership=membership,
            role=billing_contact_role,
        )

        signal = MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME
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

        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_membership_quarterly_email_strategy(
                signal,
                membership_quarterly_email_strategy(signal, membership),
                request,
                membership,
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
