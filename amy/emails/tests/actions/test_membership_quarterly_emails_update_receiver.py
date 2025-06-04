from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions.membership_quarterly_emails import (
    membership_quarterly_6_months_update_receiver,
    membership_quarterly_email_strategy,
    run_membership_quarterly_email_strategy,
)
from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
    membership_quarterly_6_months_update_signal,
)
from emails.utils import api_model_url
from fiscal.models import MembershipPersonRole, MembershipTask
from workshops.models import Event, Membership, Organization, Person, Role, Task
from workshops.tests.base import TestBase


class TestMembershipQuarterlyEmailUpdateReceiver(TestCase):
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
        self.event = Event.objects.create(
            slug="test-event",
            membership=self.membership,
            host=Organization.objects.all()[0],
        )
        learner, _ = Role.objects.get_or_create(name="learner")
        self.task = Task.objects.create(
            event=self.event,
            seat_membership=self.membership,
            person=self.person,
            role=learner,
        )

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    @patch("emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            membership_quarterly_6_months_update_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping membership_quarterly_6_months_update"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = membership_quarterly_6_months_update_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        membership_quarterly_6_months_update_signal.connect(membership_quarterly_6_months_update_receiver)
        new_receivers = membership_quarterly_6_months_update_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        request = RequestFactory().get("/")

        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )

        # Act
        with patch("emails.actions.base_action.messages_action_updated") as mock_messages_action_updated:
            membership_quarterly_6_months_update_signal.send(
                sender=self.membership,
                request=request,
                membership=self.membership,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_updated.assert_called_once_with(
            request,
            MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_updated")
    @patch("emails.actions.membership_quarterly_emails.shift_date_and_apply_current_utc_time")
    def test_email_updated(
        self,
        mock_shift_date_and_apply_current_utc_time: MagicMock,
        mock_messages_action_updated: MagicMock,
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
        scheduled_at = datetime(2024, 8, 5, 12, 0, tzinfo=UTC)
        mock_shift_date_and_apply_current_utc_time.return_value = scheduled_at

        # Act
        with patch("emails.actions.base_action.EmailController.update_scheduled_email") as mock_update_scheduled_email:
            membership_quarterly_6_months_update_signal.send(
                sender=self.membership,
                request=request,
                membership=self.membership,
            )

        # Assert
        mock_update_scheduled_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            context_json=ContextModel(
                {
                    "membership": api_model_url("membership", self.membership.pk),
                    "member_contacts": [api_model_url("person", self.person.pk)],
                    "events": [api_model_url("event", self.event.pk)],
                    "trainee_tasks": [api_model_url("task", self.task.pk)],
                    "trainees": [api_model_url("person", self.person.pk)],
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[self.person.email],
            to_header_context_json=ToHeaderModel(
                [
                    SinglePropertyLinkModel(
                        api_uri=api_model_url("person", self.person.pk),
                        property="email",
                    ),
                ]
            ),
            generic_relation_obj=self.membership,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.logger")
    @patch("emails.actions.base_action.EmailController")
    def test_previously_scheduled_email_not_existing(
        self, mock_email_controller: MagicMock, mock_logger: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME

        # Act
        membership_quarterly_6_months_update_signal.send(
            sender=self.membership,
            request=request,
            membership=self.membership,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Scheduled email for signal {signal} and generic_relation_obj={self.membership!r} does not exist."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.logger")
    @patch("emails.actions.base_action.EmailController")
    def test_multiple_previously_scheduled_emails(
        self, mock_email_controller: MagicMock, mock_logger: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME
        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )

        # Act
        membership_quarterly_6_months_update_signal.send(
            sender=self.membership,
            request=request,
            membership=self.membership,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Too many scheduled emails for signal {signal} and generic_relation_obj={self.membership!r}. "
            "Can't update them."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(self, mock_messages_missing_recipients: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.membership,
        )
        signal = MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME
        self.person.email = ""
        self.person.save()

        # Act
        membership_quarterly_6_months_update_signal.send(
            sender=self.membership,
            request=request,
            membership=self.membership,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)


class TestMembershipQuarterlyEmailUpdateIntegration(TestBase):
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
        MembershipTask.objects.create(
            person=self.hermione,
            membership=membership,
            role=billing_contact_role,
        )

        signal = MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME
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
        with patch("emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_membership_quarterly_email_strategy(
                signal,
                membership_quarterly_email_strategy(signal, membership),
                request,
                membership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("membership_edit", args=[membership.pk])
        data = {
            "name": membership.name,
            "consortium": membership.consortium,
            "public_status": membership.public_status,
            "variant": membership.variant,
            "agreement_start": membership.agreement_start,
            "agreement_end": membership.agreement_end,
            "contribution_type": membership.contribution_type,
            "registration_code": "",
            "agreement_link": "https://example.org",
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
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, f"Updated {signal}")
