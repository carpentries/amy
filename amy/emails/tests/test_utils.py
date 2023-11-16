from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone
import pytz

from emails.models import ScheduledEmail
from emails.signals import Signal
from emails.utils import (
    find_signal_by_name,
    immediate_action,
    messages_action_cancelled,
    messages_action_scheduled,
    messages_action_updated,
    messages_missing_recipients,
    messages_missing_template,
    messages_missing_template_link,
    one_month_before,
    person_from_request,
    session_condition,
)
from workshops.models import Person


class TestSessionCondition(TestCase):
    def test_session_condition(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.session = {"test": True}  # type: ignore
        # Act
        result = session_condition(value="test", request=request)
        # Assert
        self.assertEqual(result, True)


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


class TestOneMonthBefore(TestCase):
    @patch("emails.utils.datetime", wraps=datetime)
    def test_one_month_before(self, mock_datetime) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(
            2020, 1, 31, 12, 0, 0, tzinfo=pytz.UTC
        )
        start_date = date(2020, 1, 31)

        # Act
        calculated = one_month_before(start_date)

        # Assert
        self.assertEqual(calculated.tzinfo, pytz.UTC)
        self.assertEqual(calculated.date(), date(2020, 1, 1))
        self.assertEqual(calculated.timetz(), time(12, 0, 0, tzinfo=pytz.UTC))


class TestMessagesMissingRecipients(TestCase):
    @patch("emails.utils.messages.warning")
    def test_messages_missing_recipients(self, mock_messages_warning) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = "test_signal"

        # Act
        messages_missing_recipients(request=request, signal=signal)

        # Assert
        mock_messages_warning.assert_called_once_with(
            request,
            "Email action was not scheduled due to missing recipients for signal "
            f"{signal}. Please check if the persons involved have email "
            "addresses set.",
            extra_tags=settings.ONLY_FOR_ADMINS_TAG,
        )


class TestMessagesMissingTemplate(TestCase):
    @patch("emails.utils.messages.warning")
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


class TestMessagesMissingTemplateLink(TestCase):
    @patch("emails.utils.messages.warning")
    def test_messages_missing_template(self, mock_messages_warning) -> None:
        # Arrange
        request = RequestFactory().get("/")
        scheduled_email = ScheduledEmail()

        # Act
        messages_missing_template_link(request=request, scheduled_email=scheduled_email)

        # Assert
        mock_messages_warning.assert_called_once_with(
            request,
            f'Email action <a href="{ scheduled_email.get_absolute_url }">'
            f"<code>{ scheduled_email.pk }</code></a> update was not performed due"
            " to missing linked template.",
            extra_tags=settings.ONLY_FOR_ADMINS_TAG,
        )


class TestMessagesActionScheduled(TestCase):
    @patch("emails.utils.messages.info")
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


class TestMessagesActionUpdated(TestCase):
    @patch("emails.utils.messages.info")
    def test_messages_action_updated(self, mock_messages_info) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal_name = "test_signal"
        scheduled_at = timezone.now()
        scheduled_email = ScheduledEmail(scheduled_at=scheduled_at)

        # Act
        messages_action_updated(request, signal_name, scheduled_email)

        # Assert
        mock_messages_info.assert_called_once_with(
            request,
            f'Existing <a href="{scheduled_email.get_absolute_url()}">email action '
            f"({signal_name})</a> was updated.",
            extra_tags=settings.ONLY_FOR_ADMINS_TAG,
        )


class TestMessagesActionCancelled(TestCase):
    @patch("emails.utils.messages.warning")
    def test_messages_action_cancelled(self, mock_messages_warning) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal_name = "test_signal"
        scheduled_at = timezone.now()
        scheduled_email = ScheduledEmail(scheduled_at=scheduled_at)

        # Act
        messages_action_cancelled(request, signal_name, scheduled_email)

        # Assert
        mock_messages_warning.assert_called_once_with(
            request,
            f'Existing <a href="{scheduled_email.get_absolute_url()}">email action '
            f"({signal_name})</a> was cancelled.",
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
