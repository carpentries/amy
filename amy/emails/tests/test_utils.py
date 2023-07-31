from datetime import timedelta
from unittest import mock

from django.test import RequestFactory, TestCase
from django.utils import timezone
import pytz

from emails.models import ScheduledEmail
from emails.utils import (
    check_feature_flag,
    feature_flag_enabled,
    immediate_action,
    messages_action_scheduled,
    messages_missing_template,
)


class TestCheckFeatureFlag(TestCase):
    def test_check_feature_flag(self) -> None:
        with self.settings(EMAIL_MODULE_ENABLED=False):
            self.assertEqual(check_feature_flag(), False)
        with self.settings(EMAIL_MODULE_ENABLED=True):
            self.assertEqual(check_feature_flag(), True)


class TestFeatureFlagEnabled(TestCase):
    def test_feature_flag_enabled_decorator(self) -> None:
        with self.settings(EMAIL_MODULE_ENABLED=False):

            @feature_flag_enabled
            def test_func():
                return True

            self.assertEqual(test_func(), None)

        with self.settings(EMAIL_MODULE_ENABLED=True):

            @feature_flag_enabled
            def test_func():
                return True

            self.assertEqual(test_func(), True)


class TestImmediateAction(TestCase):
    def test_immediate_action(self) -> None:
        # Arrange
        now = timezone.now()

        # Act
        immediate = immediate_action()

        # Assert
        self.assertEqual(immediate.tzinfo, pytz.UTC)
        # Assert that the immediate action is scheduled for 1 hour from now,
        # with a 1 second tolerance
        self.assertTrue(immediate - timedelta(hours=1) - now < timedelta(seconds=1))


class TestMessagesMissingTemplate(TestCase):
    @mock.patch("emails.utils.messages.warning")
    def test_messages_missing_template(self, mock_messages_warning) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = "test_signal"

        # Act
        messages_missing_template(request=request, signal=signal)

        # Assert
        mock_messages_warning.assert_called_once_with(
            request,
            f"Action was not scheduled due to missing template for signal {signal}.",
        )


class TestMessagesActionScheduled(TestCase):
    @mock.patch("emails.utils.messages.info")
    def test_messages_action_scheduled(self, mock_messages_info) -> None:
        # Arrange
        request = RequestFactory().get("/")
        scheduled_email = ScheduledEmail()

        # Act
        messages_action_scheduled(request=request, scheduled_email=scheduled_email)

        # Assert
        mock_messages_info.assert_called_once_with(
            request,
            f'Action was scheduled: <a href="{scheduled_email.get_absolute_url()}">'
            f"{scheduled_email.pk}</a>.",
        )
