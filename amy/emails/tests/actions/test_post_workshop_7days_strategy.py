from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.exceptions import EmailStrategyException
from emails.actions.post_workshop_7days import (
    post_workshop_7days_strategy,
    run_post_workshop_7days_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import POST_WORKSHOP_7DAYS_SIGNAL_NAME
from emails.types import StrategyEnum
from workshops.models import Event, Organization, Person, Role, Tag, Task


class TestPostWorkshop7DaysStrategy(TestCase):
    def setUp(self) -> None:
        self.ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=self.ttt_organization,
            start=date.today() + timedelta(days=30),
            end=date.today() + timedelta(days=31),
        )
        self.swc_tag = Tag.objects.create(name="SWC")
        self.event.tags.add(self.swc_tag)

        self.instructor_role = Role.objects.create(name="instructor")
        self.instructor = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )
        self.host_role = Role.objects.create(name="host")
        self.host = Person.objects.create(personal="Test", family="Test", email="test2@example.org", username="test2")

    def test_strategy_create(self) -> None:
        # Arrange
        Task.objects.create(event=self.event, person=self.instructor, role=self.instructor_role)
        Task.objects.create(event=self.event, person=self.host, role=self.host_role)

        # Act
        result = post_workshop_7days_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        Task.objects.create(event=self.event, person=self.instructor, role=self.instructor_role)
        Task.objects.create(event=self.event, person=self.host, role=self.host_role)
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=POST_WORKSHOP_7DAYS_SIGNAL_NAME,
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
        result = post_workshop_7days_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_remove(self) -> None:
        # Arrange
        Task.objects.create(event=self.event, person=self.instructor, role=self.instructor_role)
        # Host Task intentionally not created
        # Task.objects.create(
        #     event=self.event, person=self.host, role=self.host_role
        # )
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=POST_WORKSHOP_7DAYS_SIGNAL_NAME,
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
        result = post_workshop_7days_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)

    def test_strategy_noop(self) -> None:
        # Act
        result = post_workshop_7days_strategy(self.event)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunPostWorkshop7DaysStrategy(TestCase):
    @patch("emails.actions.post_workshop_7days.post_workshop_7days_signal")
    def test_strategy_calls_create_signal(
        self,
        mock_post_workshop_7days_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        event = Event(end=date.today())

        # Act
        run_post_workshop_7days_strategy(strategy, request, event)

        # Assert
        mock_post_workshop_7days_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_end_date=date.today(),
        )

    @patch("emails.actions.post_workshop_7days.post_workshop_7days_update_signal")
    def test_strategy_calls_update_signal(
        self,
        mock_post_workshop_7days_update_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        event = Event(end=date.today())

        # Act
        run_post_workshop_7days_strategy(strategy, request, event)

        # Assert
        mock_post_workshop_7days_update_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_end_date=date.today(),
        )

    @patch("emails.actions.post_workshop_7days.post_workshop_7days_cancel_signal")
    def test_strategy_calls_cancel_signal(
        self,
        mock_post_workshop_7days_cancel_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CANCEL
        request = RequestFactory().get("/")
        event = Event(end=date.today())

        # Act
        run_post_workshop_7days_strategy(strategy, request, event)

        # Assert
        mock_post_workshop_7days_cancel_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_end_date=date.today(),
        )

    @patch("emails.actions.base_strategy.logger")
    @patch("emails.actions.post_workshop_7days.post_workshop_7days_signal")
    @patch("emails.actions.post_workshop_7days.post_workshop_7days_update_signal")
    @patch("emails.actions.post_workshop_7days.post_workshop_7days_cancel_signal")
    def test_invalid_strategy_no_signal_called(
        self,
        mock_post_workshop_7days_cancel_signal,
        mock_post_workshop_7days_update_signal,
        mock_post_workshop_7days_signal,
        mock_logger,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        event = Event(end=date.today())

        # Act
        run_post_workshop_7days_strategy(strategy, request, event)

        # Assert
        mock_post_workshop_7days_signal.send.assert_not_called()
        mock_post_workshop_7days_update_signal.send.assert_not_called()
        mock_post_workshop_7days_cancel_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(f"Strategy {strategy} for {event} is a no-op")

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")
        event = Event(end=date.today())

        # Act & Assert
        with self.assertRaises(EmailStrategyException, msg=f"Unknown strategy {strategy}"):
            run_post_workshop_7days_strategy(strategy, request, event)
