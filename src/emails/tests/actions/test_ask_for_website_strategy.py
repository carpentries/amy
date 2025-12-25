from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from src.emails.actions.ask_for_website import (
    ask_for_website_strategy,
    run_ask_for_website_strategy,
)
from src.emails.actions.exceptions import EmailStrategyException
from src.emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from src.emails.signals import ASK_FOR_WEBSITE_SIGNAL_NAME
from src.emails.types import StrategyEnum
from src.workshops.models import Event, Organization, Person, Role, Tag, Task


class TestAskForWebsiteStrategy(TestCase):
    def setUp(self) -> None:
        self.ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
        swc_tag = Tag.objects.create(name="SWC")
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=self.ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        self.event.tags.set([swc_tag])

        self.instructor_role = Role.objects.create(name="instructor")
        self.instructor1 = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )

    def test_strategy_create(self) -> None:
        # Arrange
        Task.objects.create(event=self.event, person=self.instructor1, role=self.instructor_role)

        # Act
        result = ask_for_website_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        Task.objects.create(event=self.event, person=self.instructor1, role=self.instructor_role)
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=ASK_FOR_WEBSITE_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )

        # Act
        result = ask_for_website_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_remove(self) -> None:
        # Arrange
        # Instructor Task intentionally not created
        # Task.objects.create(
        #     event=self.event, person=self.instructor1, role=self.instructor_role
        # )
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=ASK_FOR_WEBSITE_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )

        # Act
        result = ask_for_website_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)

    def test_strategy_noop(self) -> None:
        # Act
        result = ask_for_website_strategy(self.event)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunAskForWebsiteStrategy(TestCase):
    @patch("src.emails.actions.ask_for_website.ask_for_website_signal")
    def test_strategy_calls_create_signal(
        self,
        mock_ask_for_website_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_ask_for_website_strategy(strategy, request, event)

        # Assert
        mock_ask_for_website_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

    @patch("src.emails.actions.ask_for_website.ask_for_website_update_signal")
    def test_strategy_calls_update_signal(
        self,
        mock_ask_for_website_update_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_ask_for_website_strategy(strategy, request, event)

        # Assert
        mock_ask_for_website_update_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

    @patch("src.emails.actions.ask_for_website.ask_for_website_cancel_signal")
    def test_strategy_calls_cancel_signal(
        self,
        mock_ask_for_website_cancel_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CANCEL
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_ask_for_website_strategy(strategy, request, event)

        # Assert
        mock_ask_for_website_cancel_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

    @patch("src.emails.actions.base_strategy.logger")
    @patch("src.emails.actions.ask_for_website.ask_for_website_signal")
    @patch("src.emails.actions.ask_for_website.ask_for_website_update_signal")
    @patch("src.emails.actions.ask_for_website.ask_for_website_cancel_signal")
    def test_invalid_strategy_no_signal_called(
        self,
        mock_ask_for_website_cancel_signal,
        mock_ask_for_website_update_signal,
        mock_ask_for_website_signal,
        mock_logger,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_ask_for_website_strategy(strategy, request, event)

        # Assert
        mock_ask_for_website_signal.send.assert_not_called()
        mock_ask_for_website_update_signal.send.assert_not_called()
        mock_ask_for_website_cancel_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(f"Strategy {strategy} for {event} is a no-op")

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act & Assert
        with self.assertRaises(EmailStrategyException, msg=f"Unknown strategy {strategy}"):
            run_ask_for_website_strategy(strategy, request, event)
