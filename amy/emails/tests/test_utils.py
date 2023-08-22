from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone
import pytz

from emails.models import ScheduledEmail
from emails.signals import Signal
from emails.utils import (
    check_feature_flag,
    feature_flag_enabled,
    find_signal_by_name,
    immediate_action,
    messages_action_scheduled,
    messages_missing_template,
    person_from_request,
)
from workshops.models import Person


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
            extra_tags=settings.ONLY_FOR_ADMINS_TAG,
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
            extra_tags=settings.ONLY_FOR_ADMINS_TAG,
        )


class TestPersonFromRequest(TestCase):
    def test_person_from_request__no_user_field(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        # Act
        result = person_from_request(request)
        # Assert
        self.assertIsNone(result)

    def test_person_from_request__anonymous_user(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        # Act
        result = person_from_request(request)
        # Assert
        self.assertIsNone(result)

    def test_person_from_request__authenticated_user(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        user = Person.objects.create()
        request.user = user
        # Act
        result = person_from_request(request)
        # Assert
        self.assertEqual(result, user)


class TestFindSignalByName(TestCase):
    def test_find_signal_by_name__empty_signal_list(self) -> None:
        # Arrange
        all_signals = []

        # Act
        result = find_signal_by_name("test", all_signals)

        # Assert
        self.assertEqual(result, None)

    def test_find_signal_by_name__signal_not_found(self) -> None:
        # Arrange
        all_signals = [Signal(signal_name="not_found", context_type=dict)]

        # Act
        result = find_signal_by_name("test", all_signals)

        # Assert
        self.assertEqual(result, None)

    def test_find_signal_by_name__signal_found(self) -> None:
        # Arrange
        expected = Signal(signal_name="test", context_type=dict)
        all_signals = [Signal(signal_name="not_found", context_type=dict), expected]

        # Act
        result = find_signal_by_name("test", all_signals)

        # Assert
        self.assertEqual(result, expected)
