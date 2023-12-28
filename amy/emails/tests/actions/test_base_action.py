from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone as django_timezone

from emails.actions.base_action import (
    BaseAction,
    BaseActionCancel,
    BaseActionUpdate,
    feature_flag_enabled,
)
from emails.controller import (
    EmailControllerMissingRecipientsException,
    EmailControllerMissingTemplateException,
)
from emails.models import EmailTemplate, ScheduledEmail
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import SignalNameEnum
from workshops.models import Event, Organization


class TestFeatureFlagEnabled(TestCase):
    feature_flag = "TEST_FEATURE_FLAG"
    signal_name = "test_signal_name"

    @patch("emails.actions.base_action.logger")
    def test_feature_flag_enabled__missing_request(self, mock_logger: MagicMock):
        # Arrange
        kwargs = {}

        # Act
        result = feature_flag_enabled(self.feature_flag, self.signal_name, **kwargs)

        # Assert
        self.assertEqual(result, False)
        mock_logger.debug.assert_called_once_with(
            f"Cannot check {self.feature_flag} feature flag, `request` parameter "
            f"to {self.signal_name} is missing"
        )

    @override_settings(FLAGS={feature_flag: [("boolean", False)]})
    @patch("emails.actions.base_action.logger")
    def test_feature_flag_enabled__feature_flag_disabled(self, mock_logger: MagicMock):
        # Arrange
        request = RequestFactory().get("/")

        # Act
        result = feature_flag_enabled(
            self.feature_flag, self.signal_name, request=request
        )

        # Assert
        self.assertEqual(result, False)
        mock_logger.debug.assert_called_once_with(
            f"{self.feature_flag} feature flag not set, skipping {self.signal_name}"
        )

    @override_settings(FLAGS={feature_flag: [("boolean", True)]})
    @patch("emails.actions.base_action.logger")
    def test_feature_flag_enabled(self, mock_logger: MagicMock):
        # Arrange
        request = RequestFactory().get("/")

        # Act
        result = feature_flag_enabled(
            self.feature_flag, self.signal_name, request=request
        )

        # Assert
        self.assertEqual(result, True)


class BaseActionForTesting(BaseAction):
    signal = SignalNameEnum.persons_merged

    def get_scheduled_at(self, **kwargs) -> datetime:
        return datetime(2023, 10, 18, 23, 00, tzinfo=timezone.utc)

    def get_context(self, **kwargs) -> dict[str, Any]:
        return {}

    def get_context_json(self, **kwargs) -> ContextModel:
        return ContextModel({})

    def get_generic_relation_object(self, context: dict[str, Any], **kwargs) -> Any:
        return 0

    def get_recipients(self, context: dict[str, Any], **kwargs) -> list[str]:
        return []

    def get_recipients_context_json(
        self, context: dict[str, Any], **kwargs
    ) -> ToHeaderModel:
        return ToHeaderModel([])


class BaseActionUpdateForTesting(BaseActionUpdate):
    signal = SignalNameEnum.persons_merged

    def get_scheduled_at(self, **kwargs) -> datetime:
        return datetime(2023, 10, 18, 23, 00, tzinfo=timezone.utc)

    def get_context(self, **kwargs) -> dict[str, Any]:
        return {}

    def get_context_json(self, **kwargs) -> ContextModel:
        return ContextModel({})

    def get_generic_relation_object(self, context: dict[str, Any], **kwargs) -> Any:
        return Event.objects.get_or_create(
            defaults=dict(
                host=Organization.objects.first(),
                administrator=Organization.objects.first(),
            ),
            slug="test-event",
        )[0]

    def get_recipients(self, context: dict[str, Any], **kwargs) -> list[str]:
        return []

    def get_recipients_context_json(
        self, context: dict[str, Any], **kwargs
    ) -> ToHeaderModel:
        return ToHeaderModel([])


class BaseActionCancelForTesting(BaseActionCancel):
    signal = SignalNameEnum.persons_merged

    def get_scheduled_at(self, **kwargs) -> datetime:
        return datetime(2023, 10, 18, 23, 00, tzinfo=timezone.utc)

    def get_context(self, **kwargs) -> dict[str, Any]:
        return {}

    def get_context_json(self, **kwargs) -> ContextModel:
        return ContextModel({})

    def get_generic_relation_object(self, context: dict[str, Any], **kwargs) -> Any:
        return Event.objects.get_or_create(
            defaults=dict(
                host=Organization.objects.first(),
                administrator=Organization.objects.first(),
            ),
            slug="test-event",
        )[0]

    def get_recipients(self, context: dict[str, Any], **kwargs) -> list[str]:
        return []

    def get_recipients_context_json(
        self, context: dict[str, Any], **kwargs
    ) -> ToHeaderModel:
        return ToHeaderModel([])


class TestBaseAction(TestCase):
    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.person_from_request")
    @patch("emails.actions.base_action.EmailController.schedule_email")
    @patch("emails.actions.base_action.messages_action_scheduled")
    def test_call(
        self,
        mock_action_scheduled: MagicMock,
        mock_schedule_email: MagicMock,
        mock_person_from_request: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionForTesting()

        scheduled_email = MagicMock()
        mock_schedule_email.return_value = scheduled_email

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)
        context = instance.get_context()

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", instance.signal, **kwargs
        )
        mock_person_from_request.assert_called_once_with(request)
        mock_schedule_email.assert_called_once_with(
            signal=instance.signal,
            context_json=ContextModel({}),
            scheduled_at=instance.get_scheduled_at(),
            to_header=instance.get_recipients(context),
            to_header_context_json=ToHeaderModel([]),
            generic_relation_obj=instance.get_generic_relation_object(context),
            author=mock_person_from_request.return_value,
        )
        mock_action_scheduled.assert_called_once_with(
            request, instance.signal, scheduled_email
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=False)
    @patch("emails.actions.base_action.EmailController.schedule_email")
    def test_call__feature_flag_not_enabled(
        self,
        mock_schedule_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionForTesting()

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        result = instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", instance.signal, **kwargs
        )
        mock_schedule_email.assert_not_called()
        self.assertIsNone(result)

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.EmailController.schedule_email")
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_call__missing_recipients(
        self,
        mock_messages_missing_recipients: MagicMock,
        mock_schedule_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionForTesting()
        mock_schedule_email.side_effect = EmailControllerMissingRecipientsException()

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", instance.signal, **kwargs
        )
        mock_messages_missing_recipients.assert_called_once_with(
            request, instance.signal
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.EmailController.schedule_email")
    @patch("emails.actions.base_action.messages_missing_template")
    def test_call__missing_template(
        self,
        mock_messages_missing_template: MagicMock,
        mock_schedule_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionForTesting()
        mock_schedule_email.side_effect = EmailTemplate.DoesNotExist()

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", instance.signal, **kwargs
        )
        mock_messages_missing_template.assert_called_once_with(request, instance.signal)


class TestBaseActionUpdate(TestCase):
    def setUpEmailTemplate(self, signal: SignalNameEnum) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template1",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    def setUpScheduledEmail(
        self, template: EmailTemplate, generic_object: Any
    ) -> ScheduledEmail:
        return ScheduledEmail.objects.create(
            scheduled_at=django_timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net", "harry@potter.co.uk"],
            from_header="",
            reply_to_header="",
            cc_header=[],
            bcc_header=[],
            subject="Test subject",
            body="Test content",
            template=template,
            generic_relation=generic_object,
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.person_from_request")
    @patch("emails.actions.base_action.EmailController.update_scheduled_email")
    @patch("emails.actions.base_action.messages_action_updated")
    def test_call(
        self,
        mock_action_updated: MagicMock,
        mock_update_scheduled_email: MagicMock,
        mock_person_from_request: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionUpdateForTesting()
        event = instance.get_generic_relation_object({})

        template = self.setUpEmailTemplate(instance.signal)
        scheduled_email = self.setUpScheduledEmail(template, event)

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)
        context = instance.get_context()

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_update", **kwargs
        )
        mock_person_from_request.assert_called_once_with(request)
        mock_update_scheduled_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            context_json=ContextModel({}),
            scheduled_at=instance.get_scheduled_at(),
            to_header=instance.get_recipients(context),
            to_header_context_json=ToHeaderModel([]),
            generic_relation_obj=instance.get_generic_relation_object(context),
            author=mock_person_from_request.return_value,
        )
        mock_action_updated.assert_called_once_with(
            request, instance.signal, mock_update_scheduled_email.return_value
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=False)
    @patch("emails.actions.base_action.EmailController.update_scheduled_email")
    def test_call__feature_flag_not_enabled(
        self,
        mock_update_scheduled_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionUpdateForTesting()

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        result = instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_update", **kwargs
        )
        mock_update_scheduled_email.assert_not_called()
        self.assertIsNone(result)

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.logger")
    def test_call__no_scheduled_email(
        self,
        mock_logger: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionUpdateForTesting()
        event = instance.get_generic_relation_object({})

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        result = instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_update", **kwargs
        )
        self.assertIsNone(result)
        mock_logger.warning.assert_called_once_with(
            f"Scheduled email for signal {instance.signal} and "
            f"generic_relation_obj={event!r} does not exist."
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.logger")
    def test_call__multiple_scheduled_emails(
        self,
        mock_logger: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionUpdateForTesting()
        event = instance.get_generic_relation_object({})

        template = self.setUpEmailTemplate(instance.signal)
        self.setUpScheduledEmail(template, event)
        self.setUpScheduledEmail(template, event)

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        result = instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_update", **kwargs
        )
        self.assertIsNone(result)
        mock_logger.warning.assert_called_once_with(
            f"Too many scheduled emails for signal {instance.signal} and "
            f"generic_relation_obj={event!r}. Can't update them."
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.EmailController.update_scheduled_email")
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_call__missing_recipients(
        self,
        mock_messages_missing_recipients: MagicMock,
        mock_update_scheduled_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionUpdateForTesting()
        event = instance.get_generic_relation_object({})
        mock_update_scheduled_email.side_effect = (
            EmailControllerMissingRecipientsException()
        )

        template = self.setUpEmailTemplate(instance.signal)
        self.setUpScheduledEmail(template, event)

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_update", **kwargs
        )
        mock_messages_missing_recipients.assert_called_once_with(
            request, instance.signal
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.EmailController.update_scheduled_email")
    @patch("emails.actions.base_action.messages_missing_template_link")
    def test_call__missing_template_link(
        self,
        mock_messages_missing_template_link: MagicMock,
        mock_update_scheduled_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionUpdateForTesting()
        event = instance.get_generic_relation_object({})
        mock_update_scheduled_email.side_effect = (
            EmailControllerMissingTemplateException()
        )

        template = self.setUpEmailTemplate(instance.signal)
        scheduled_email = self.setUpScheduledEmail(template, event)

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_update", **kwargs
        )
        mock_messages_missing_template_link.assert_called_once_with(
            request, scheduled_email
        )


class TestBaseActionCancel(TestCase):
    def setUpEmailTemplate(self, signal: SignalNameEnum) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template1",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    def setUpScheduledEmail(
        self, template: EmailTemplate, generic_object: Any
    ) -> ScheduledEmail:
        return ScheduledEmail.objects.create(
            scheduled_at=django_timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net", "harry@potter.co.uk"],
            from_header="",
            reply_to_header="",
            cc_header=[],
            bcc_header=[],
            subject="Test subject",
            body="Test content",
            template=template,
            generic_relation=generic_object,
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.person_from_request")
    @patch("emails.actions.base_action.EmailController.cancel_email")
    @patch("emails.actions.base_action.messages_action_cancelled")
    def test_call(
        self,
        mock_action_cancelled: MagicMock,
        mock_cancel_email: MagicMock,
        mock_person_from_request: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionCancelForTesting()
        event = instance.get_generic_relation_object({})

        template = self.setUpEmailTemplate(instance.signal)
        scheduled_email = self.setUpScheduledEmail(template, event)

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_remove", **kwargs
        )
        mock_person_from_request.assert_called_once_with(request)
        mock_cancel_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            author=mock_person_from_request.return_value,
        )
        mock_action_cancelled.assert_called_once_with(
            request, instance.signal, mock_cancel_email.return_value
        )

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.person_from_request")
    @patch("emails.actions.base_action.EmailController.cancel_email")
    @patch("emails.actions.base_action.messages_action_cancelled")
    def test_call__multiple_scheduled_emails(
        self,
        mock_action_cancelled: MagicMock,
        mock_cancel_email: MagicMock,
        mock_person_from_request: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionCancelForTesting()
        event = instance.get_generic_relation_object({})

        template = self.setUpEmailTemplate(instance.signal)
        self.setUpScheduledEmail(template, event)
        self.setUpScheduledEmail(template, event)

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_remove", **kwargs
        )
        self.assertEqual(mock_person_from_request.call_count, 2)
        self.assertEqual(mock_cancel_email.call_count, 2)
        self.assertEqual(mock_action_cancelled.call_count, 2)

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=False)
    @patch("emails.actions.base_action.EmailController.cancel_email")
    def test_call__feature_flag_not_enabled(
        self,
        mock_cancel_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionCancelForTesting()

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        result = instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_remove", **kwargs
        )
        mock_cancel_email.assert_not_called()
        self.assertIsNone(result)

    @patch("emails.actions.base_action.feature_flag_enabled", return_value=True)
    @patch("emails.actions.base_action.EmailController.cancel_email")
    @patch("emails.actions.base_action.messages_action_cancelled")
    def test_call__no_scheduled_emails(
        self,
        mock_action_cancelled: MagicMock,
        mock_cancel_email: MagicMock,
        mock_feature_flag_enabled: MagicMock,
    ) -> None:
        # Arrange
        instance = BaseActionCancelForTesting()

        # Act
        sender = MagicMock()
        request = RequestFactory().get("/")
        kwargs = {"request": request}
        instance(sender, **kwargs)

        # Assert
        mock_feature_flag_enabled.assert_called_once_with(
            "EMAIL_MODULE", f"{instance.signal}_remove", **kwargs
        )
        mock_cancel_email.assert_not_called()
        mock_action_cancelled.assert_not_called()
