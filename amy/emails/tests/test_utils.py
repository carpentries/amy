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
            "Email action was not scheduled due to missing template for signal "
            f"{signal}.",
        )


class TestMessagesActionScheduled(TestCase):
    @mock.patch("emails.utils.messages.info")
    def test_messages_action_scheduled(self, mock_messages_info) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal_name = "test_signal"
        scheduled_at = timezone.now()
        scheduled_email = ScheduledEmail(scheduled_at=scheduled_at)

        # Act
        messages_action_scheduled(request, signal_name, scheduled_email)

        # Assert
        mock_messages_info.assert_called_once_with(
            request,
            f"New email action ({signal_name}) was scheduled to run "
            f'<relative-time datetime="{scheduled_at}"></relative-time>: '
            f'<a href="{scheduled_email.get_absolute_url()}"><code>'
            f"{scheduled_email.pk}</code></a>.",
        )
