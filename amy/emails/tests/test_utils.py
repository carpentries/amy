from datetime import UTC, date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import MagicMock, call, patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone
from jinja2 import DebugUndefined, Environment

from emails.models import ScheduledEmail
from emails.signals import Signal
from emails.utils import (
    build_context_from_dict,
    build_context_from_list,
    combine_date_with_current_utc_time,
    find_model_instance,
    find_signal_by_name,
    immediate_action,
    jinjanify,
    map_api_uri_to_model_or_value,
    map_single_api_uri_to_model_or_value,
    messages_action_cancelled,
    messages_action_scheduled,
    messages_action_updated,
    messages_missing_recipients,
    messages_missing_template,
    messages_missing_template_link,
    one_month_before,
    person_from_request,
    scalar_value_from_type,
    session_condition,
    shift_date_and_apply_current_utc_time,
    two_months_after,
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
        self.assertEqual(immediate.tzinfo, UTC)
        # Assert that the immediate action is scheduled for 1 hour from now,
        # with a 1 second tolerance
        self.assertTrue(immediate - timedelta(hours=1) - now < timedelta(seconds=1))


class TestCombineDateWithCurrentUtcTime(TestCase):
    @patch("emails.utils.datetime", wraps=datetime)
    def test_combine_date_with_current_utc_time(self, mock_datetime) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2020, 1, 31, 12, 1, 2, tzinfo=UTC)
        date_to_combine = date(1999, 12, 31)

        # Act
        calculated = combine_date_with_current_utc_time(date_to_combine)

        # Assert
        self.assertEqual(calculated.tzinfo, UTC)
        self.assertEqual(calculated.date(), date(1999, 12, 31))
        self.assertEqual(calculated.timetz(), time(12, 1, 2, tzinfo=UTC))


class TestShiftDateAndApplyCurrentUtcTime(TestCase):
    @patch("emails.utils.datetime", wraps=datetime)
    def test_shift_date_and_apply_current_utc_time(self, mock_datetime) -> None:
        # Arrange
        mocked_datetime = datetime(2020, 1, 31, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mocked_datetime
        date_to_shift = date(1999, 12, 31)
        offset = timedelta(days=1, hours=1, minutes=2, seconds=3)

        # Act
        shifted = shift_date_and_apply_current_utc_time(date_to_shift, offset)

        # Assert
        self.assertEqual(shifted.tzinfo, UTC)
        self.assertEqual(shifted.date(), date(2000, 1, 1))
        self.assertEqual(shifted.timetz(), time(12, 0, 0, tzinfo=UTC))


class TestOneMonthBefore(TestCase):
    @patch("emails.utils.datetime", wraps=datetime)
    def test_one_month_before(self, mock_datetime) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2020, 1, 31, 12, 0, 0, tzinfo=UTC)
        start_date = date(2020, 1, 31)

        # Act
        calculated = one_month_before(start_date)

        # Assert
        self.assertEqual(calculated.tzinfo, UTC)
        self.assertEqual(calculated.date(), date(2020, 1, 1))
        self.assertEqual(calculated.timetz(), time(12, 0, 0, tzinfo=UTC))


class TestTwoMonthsAfter(TestCase):
    @patch("emails.utils.datetime", wraps=datetime)
    def test_two_months_after(self, mock_datetime) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2020, 1, 31, 12, 0, 0, tzinfo=UTC)
        start_date = date(2020, 1, 31)

        # Act
        calculated = two_months_after(start_date)

        # Assert
        self.assertEqual(calculated.tzinfo, UTC)
        self.assertEqual(calculated.date(), date(2020, 3, 31))
        self.assertEqual(calculated.timetz(), time(12, 0, 0, tzinfo=UTC))


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
        name = (
            scheduled_email.template.name if scheduled_email.template else signal_name
        )

        # Act
        messages_action_scheduled(request, signal_name, scheduled_email)

        # Assert
        mock_messages_info.assert_called_once_with(
            request,
            f"New email action was scheduled to run "
            f'<relative-time datetime="{scheduled_at}"></relative-time>: '
            f'<a href="{scheduled_email.get_absolute_url()}"><code>'
            f"{name}</code></a>.",
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
        name = (
            scheduled_email.template.name if scheduled_email.template else signal_name
        )

        # Act
        messages_action_updated(request, signal_name, scheduled_email)

        # Assert
        mock_messages_info.assert_called_once_with(
            request,
            f'Existing <a href="{scheduled_email.get_absolute_url()}">email action '
            f"({name})</a> was updated.",
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
        name = (
            scheduled_email.template.name if scheduled_email.template else signal_name
        )

        # Act
        messages_action_cancelled(request, signal_name, scheduled_email)

        # Assert
        mock_messages_warning.assert_called_once_with(
            request,
            f'Existing <a href="{scheduled_email.get_absolute_url()}">email action '
            f"({name})</a> was cancelled.",
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


class TestJinjanify(TestCase):
    def test_jinjanify(self) -> None:
        # Arrange
        engine = Environment(autoescape=True, undefined=DebugUndefined)
        template = "Hello, {{ name }}!"
        context = {"name": "John"}

        # Act
        result = jinjanify(engine, template, context)

        # Assert
        self.assertEqual(result, "Hello, John!")


class TestScalarValueFromType(TestCase):
    def test_scalar_value_from_type(self) -> None:
        # Arrange
        tz = dt_timezone(timedelta(hours=1, minutes=30))
        args = [
            ("str", "test", "test"),
            ("int", "123", 123),
            ("float", "123.456", 123.456),
            ("bool", "True", True),
            ("bool", "true", True),
            ("bool", "t", True),
            ("bool", "1", True),
            ("bool", "False", False),
            ("bool", "false", False),
            ("bool", "f", False),
            (
                "date",
                "2020-01-01T12:01:03+01:30",
                datetime(2020, 1, 1, 12, 1, 3, tzinfo=tz),
            ),
            (
                "date",
                "2020-01-01T12:01:03Z",
                datetime(2020, 1, 1, 12, 1, 3, tzinfo=timezone.utc),
            ),
            (
                "date",
                "2020-01-01T12:01:03+00:00",
                datetime(2020, 1, 1, 12, 1, 3, tzinfo=timezone.utc),
            ),
            ("none", "", None),
            ("none", "whatever", None),
        ]

        # Act & Assert
        for type_, value, expected in args:
            with self.subTest(type=type_, value=value):
                result = scalar_value_from_type(type_, value)
                self.assertEqual(result, expected)

    def test_scalar_value_from_type__unsupported_type(self) -> None:
        # Arrange
        type_ = "unsupported"
        value = "test"

        # Act & Assert
        with self.assertRaises(ValueError) as cm:
            scalar_value_from_type(type_, value)
        self.assertEqual(
            str(cm.exception),
            f"Unsupported scalar type {type_!r} (value {value!r}).",
        )

    def test_scalar_value_from_type__failed_to_parse(self) -> None:
        # Arrange
        args = [
            ("int", "test"),
            ("date", "test"),
        ]

        # Act & Assert
        for type_, value in args:
            with self.subTest(type=type_, value=value):
                with self.assertRaises(ValueError) as cm:
                    scalar_value_from_type(type_, value)
                self.assertEqual(
                    str(cm.exception),
                    f"Failed to parse {value!r} for type {type_!r}.",
                )


class TestFindModelInstance(TestCase):
    def test_find_model_instance(self) -> None:
        # Arrange
        person = Person.objects.create()
        model_name = "person"
        model_pk = person.pk

        # Act
        result = find_model_instance(model_name, model_pk)

        # Assert
        self.assertEqual(result, person)

    def test_find_model_instance__model_doesnt_exist(self) -> None:
        # Arrange
        model_name = "fake_model"
        model_pk = 1

        # Act & Assert
        with self.assertRaises(ValueError) as cm:
            find_model_instance(model_name, model_pk)
        self.assertEqual(
            str(cm.exception),
            f"Model {model_name!r} not found.",
        )

    def test_find_model_instance__invalid_model_pk(self) -> None:
        # Arrange
        model_name = "person"
        model_pk = "invalid_pk"

        # Act & Assert
        with self.assertRaises(ValueError) as cm:
            find_model_instance(model_name, model_pk)
        self.assertEqual(
            str(cm.exception),
            f"Failed to parse pk {model_pk!r} for model {model_name!r}: Field "
            f"'id' expected a number but got '{model_pk}'.",
        )

    def test_find_model_instance__model_instance_doesnt_exist(self) -> None:
        # Arrange
        model_name = "person"
        model_pk = 1

        # Act & Assert
        with self.assertRaises(ValueError) as cm:
            find_model_instance(model_name, model_pk)
        self.assertEqual(
            str(cm.exception),
            f"Model {model_name!r} with pk {model_pk!r} not found.",
        )


class TestMapSingleApiUriToModelOrValue(TestCase):
    @patch("emails.utils.scalar_value_from_type")
    def test_map_single_api_uri_to_model_or_value__scalar(
        self, mock_scalar_value_from_type: MagicMock
    ) -> None:
        # Arrange
        uri = "value:str#test"
        # Act
        map_single_api_uri_to_model_or_value(uri)
        # Assert
        mock_scalar_value_from_type.assert_called_once_with("str", "test")

    @patch("emails.utils.find_model_instance")
    def test_map_single_api_uri_to_model_or_value__model(
        self, mock_find_model_instance: MagicMock
    ) -> None:
        # Arrange
        uri = "api:person#1"
        # Act
        map_single_api_uri_to_model_or_value(uri)
        # Assert
        mock_find_model_instance.assert_called_once_with("person", 1)

    def test_map_single_api_uri_to_model_or_value__unsupported_uri(self) -> None:
        # Arrange
        uris = [
            "invalid_uri",
            "api2://",
            "api2:model#1",
        ]
        # Act & Assert
        for uri in uris:
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError) as cm:
                    map_single_api_uri_to_model_or_value(uri)
                self.assertEqual(str(cm.exception), f"Unsupported URI {uri!r}.")

    def test_map_single_api_uri_to_model_or_value__unparsable_uri(self) -> None:
        # Arrange
        uris = [
            "api://",
            "api:",
            "api:model#test",
        ]
        # Act & Assert
        for uri in uris:
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError) as cm:
                    map_single_api_uri_to_model_or_value(uri)
                self.assertEqual(str(cm.exception), f"Failed to parse URI {uri!r}.")


class TestMapApiUriToModelOrValue(TestCase):
    @patch("emails.utils.map_single_api_uri_to_model_or_value")
    def test_map_api_uri_to_model_or_value(
        self, mock_map_single_api_uri_to_model_or_value: MagicMock
    ) -> None:
        # Arrange
        single_uri_arg = "fake_uri"
        multiple_uris_arg = ["fake_uri1", "fake_uri2"]

        # Act
        map_api_uri_to_model_or_value(single_uri_arg)
        map_api_uri_to_model_or_value(multiple_uris_arg)

        # Assert
        mock_map_single_api_uri_to_model_or_value.assert_has_calls(
            [call("fake_uri"), call("fake_uri1"), call("fake_uri2")]
        )


class TestBuildContextFromDict(TestCase):
    @patch("emails.utils.map_api_uri_to_model_or_value")
    def test_build_context_from_dict(
        self, mock_map_api_uri_to_model_or_value: MagicMock
    ) -> None:
        # Arrange
        context = {"key1": "uri1", "key2": "uri2", "key3": ["uri3", "uri4"]}
        # Act
        build_context_from_dict(context)
        # Assert
        mock_map_api_uri_to_model_or_value.assert_has_calls(
            [call("uri1"), call("uri2"), call(["uri3", "uri4"])]
        )

    def test_integration(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", email="test1@example.org")
        person2 = Person.objects.create(username="test2", email="test2@example.org")
        context = {
            "person1": f"api:person#{person1.pk}",
            "list": [f"api:person#{person2.pk}", "value:str#test"],
        }

        # Act
        result = build_context_from_dict(context)

        # Assert
        self.assertEqual(result, {"person1": person1, "list": [person2, "test"]})


class TestBuildContextFromList(TestCase):
    @patch("emails.utils.map_api_uri_to_model_or_value")
    def test_build_context_from_list(
        self, mock_map_api_uri_to_model_or_value: MagicMock
    ) -> None:
        # Arrange
        context = [{"api_uri": "uri1", "property": "email"}, {"value_uri": "uri2"}]
        # Act
        build_context_from_list(context)
        # Assert
        mock_map_api_uri_to_model_or_value.assert_has_calls(
            [call("uri1"), call("uri2")]
        )

    def test_integration(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", email="test1@example.org")
        context = [
            {"api_uri": f"api:person#{person1.pk}", "property": "email"},
            {"value_uri": "value:str#test2@example.org"},
        ]

        # Act
        result = build_context_from_list(context)

        # Assert
        self.assertEqual(result, ["test1@example.org", "test2@example.org"])
