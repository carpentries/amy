from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings

from src.emails.actions.instructor_badge_awarded import (
    instructor_badge_awarded_update_receiver,
)
from src.emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
    instructor_badge_awarded_update_signal,
)
from src.emails.utils import api_model_url, scalar_value_url
from src.workshops.models import Award, Badge, Person
from src.workshops.tests.base import TestBase


class TestInstructorBadgeAwardedUpdateReceiver(TestCase):
    def setUp(self) -> None:
        self.badge = Badge.objects.create(name="instructor")
        self.person = Person.objects.create(email="test@example.org")
        self.award = Award.objects.create(badge=self.badge, person=self.person)

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
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
            instructor_badge_awarded_update_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping instructor_badge_awarded_update"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_badge_awarded_update_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_badge_awarded_update_signal.connect(instructor_badge_awarded_update_receiver)
        new_receivers = instructor_badge_awarded_update_signal.receivers[:]

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
            generic_relation=self.award,
        )

        # Act
        with patch("src.emails.actions.base_action.messages_action_updated") as mock_messages_action_updated:
            instructor_badge_awarded_update_signal.send(
                sender=self.award,
                request=request,
                person_id=self.person.pk,
                award_id=self.award.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_updated.assert_called_once_with(
            request,
            INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_action_updated")
    @patch("src.emails.actions.instructor_badge_awarded.immediate_action")
    def test_email_updated(
        self,
        mock_immediate_action: MagicMock,
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
            generic_relation=self.award,
        )
        scheduled_at = datetime(2023, 8, 5, 12, 0, tzinfo=UTC)
        mock_immediate_action.return_value = scheduled_at

        # Act
        with patch(
            "src.emails.actions.base_action.EmailController.update_scheduled_email"
        ) as mock_update_scheduled_email:
            instructor_badge_awarded_update_signal.send(
                sender=self.award,
                request=request,
                person_id=self.person.pk,
                award_id=self.award.pk,
            )

        # Assert
        mock_update_scheduled_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            context_json=ContextModel(
                {
                    "person": api_model_url("person", self.person.pk),
                    "award": api_model_url("award", self.award.pk),
                    "award_id": scalar_value_url("int", str(self.award.pk)),
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
            generic_relation_obj=self.award,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.logger")
    @patch("src.emails.actions.base_action.EmailController")
    def test_previously_scheduled_email_not_existing(
        self, mock_email_controller: MagicMock, mock_logger: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME
        award = self.award

        # Act
        instructor_badge_awarded_update_signal.send(
            sender=award,
            request=request,
            person_id=award.person.pk,
            award_id=award.pk,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Scheduled email for signal {signal} and generic_relation_obj={award!r} does not exist."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.logger")
    @patch("src.emails.actions.base_action.EmailController")
    def test_multiple_previously_scheduled_emails(
        self, mock_email_controller: MagicMock, mock_logger: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME
        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.award,
        )
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.award,
        )
        award = self.award

        # Act
        instructor_badge_awarded_update_signal.send(
            sender=award,
            request=request,
            person_id=award.person.pk,
            award_id=award.pk,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Too many scheduled emails for signal {signal} and generic_relation_obj={award!r}. Can't update them."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_missing_recipients")
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
            generic_relation=self.award,
        )
        signal = INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME
        self.person.email = ""
        self.person.save()

        # Act
        instructor_badge_awarded_update_signal.send(
            sender=self.award,
            request=request,
            person_id=self.award.person.pk,
            award_id=self.award.pk,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)


class TestInstructorBadgeAwardedUpdateIntegration(TestBase):
    # Currently not possible to edit awards.
    pass
