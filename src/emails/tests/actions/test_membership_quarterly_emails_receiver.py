from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from src.emails.actions.membership_quarterly_emails import (
    membership_quarterly_3_months_receiver,
)
from src.emails.models import EmailTemplate, ScheduledEmail
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
    membership_quarterly_3_months_signal,
)
from src.emails.utils import api_model_url
from src.fiscal.models import MembershipPersonRole, MembershipTask
from src.workshops.models import Event, Membership, Organization, Person, Role, Task
from src.workshops.tests.base import TestBase


class TestMembershipQuarterlyEmailReceiver(TestCase):
    @patch("src.emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            membership_quarterly_3_months_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping membership_quarterly_3_months"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = membership_quarterly_3_months_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        membership_quarterly_3_months_signal.connect(membership_quarterly_3_months_receiver)
        new_receivers = membership_quarterly_3_months_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        person = Person.objects.create(email="test@example.org")
        membership = Membership.objects.create(
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
            person=person,
            membership=membership,
            role=billing_contact_role,
        )

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=membership_quarterly_3_months_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        # Act
        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_messages_action_scheduled:
            membership_quarterly_3_months_signal.send(
                sender=membership,
                request=request,
                membership=membership,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_scheduled.assert_called_once_with(
            request,
            membership_quarterly_3_months_signal.signal_name,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_action_scheduled")
    @patch("src.emails.actions.membership_quarterly_emails.shift_date_and_apply_current_utc_time")
    def test_email_scheduled(
        self,
        mock_shift_date_and_apply_current_utc_time: MagicMock,
        mock_messages_action_scheduled: MagicMock,
    ) -> None:
        # Arrange
        person = Person.objects.create(email="test@example.org")
        membership = Membership.objects.create(
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
            person=person,
            membership=membership,
            role=billing_contact_role,
        )
        event = Event.objects.create(
            slug="test-event",
            membership=membership,
            host=Organization.objects.all()[0],
        )
        learner, _ = Role.objects.get_or_create(name="learner")
        task = Task.objects.create(
            event=event,
            seat_membership=membership,
            person=person,
            role=learner,
        )
        request = RequestFactory().get("/")

        scheduled_at = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_shift_date_and_apply_current_utc_time.return_value = scheduled_at
        signal = membership_quarterly_3_months_signal.signal_name

        # Act
        with patch("src.emails.actions.base_action.EmailController.schedule_email") as mock_schedule_email:
            membership_quarterly_3_months_signal.send(
                sender=membership,
                request=request,
                membership=membership,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context_json=ContextModel(
                {
                    "membership": api_model_url("membership", membership.pk),
                    "member_contacts": [api_model_url("person", person.pk)],
                    "events": [api_model_url("event", event.pk)],
                    "trainee_tasks": [api_model_url("task", task.pk)],
                    "trainees": [api_model_url("person", person.pk)],
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[person.email],
            to_header_context_json=ToHeaderModel(
                [
                    SinglePropertyLinkModel(
                        api_uri=api_model_url("person", person.pk),
                        property="email",
                    ),
                ]
            ),
            generic_relation_obj=membership,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(self, mock_messages_missing_recipients: MagicMock) -> None:
        # Arrange
        person = Person.objects.create()  # no email will cause missing recipients error
        membership = Membership.objects.create(
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
            person=person,
            membership=membership,
            role=billing_contact_role,
        )
        request = RequestFactory().get("/")
        signal = membership_quarterly_3_months_signal.signal_name

        # Act
        membership_quarterly_3_months_signal.send(
            sender=membership,
            request=request,
            membership=membership,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_missing_template")
    def test_missing_template(self, mock_messages_missing_template: MagicMock) -> None:
        # Arrange
        person = Person.objects.create(email="test@example.org")
        membership = Membership.objects.create(
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
            person=person,
            membership=membership,
            role=billing_contact_role,
        )
        request = RequestFactory().get("/")
        signal = membership_quarterly_3_months_signal.signal_name

        # Act
        membership_quarterly_3_months_signal.send(
            sender=membership,
            request=request,
            membership=membership,
        )

        # Assert
        mock_messages_missing_template.assert_called_once_with(request, signal)


class TestMembershipQuarterlyEmailReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()

        membership = Membership.objects.create(
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

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
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
