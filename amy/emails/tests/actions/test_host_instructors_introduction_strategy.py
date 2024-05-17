from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.host_instructors_introduction import (
    EmailStrategyException,
    host_instructors_introduction_strategy,
    run_host_instructors_introduction_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import HOST_INSTRUCTORS_INTRODUCTION_SIGNAL_NAME
from emails.types import StrategyEnum
from workshops.models import Event, Organization, Person, Role, Tag, Task


class TestHostInstructorsIntroductionStrategy(TestCase):
    def setUp(self) -> None:
        self.ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=self.ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        self.ttt_tag = Tag.objects.create(name="TTT")
        self.event.tags.add(self.ttt_tag)

        self.instructor_role = Role.objects.create(name="instructor")
        self.instructor1 = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )
        self.instructor2 = Person.objects.create(
            personal="Test", family="Test", email="test2@example.org", username="test2"
        )
        self.host_role = Role.objects.create(name="host")
        self.host = Person.objects.create(
            personal="Test", family="Test", email="test3@example.org", username="test3"
        )

    def test_strategy_create(self) -> None:
        # Arrange
        Task.objects.create(
            event=self.event, person=self.instructor1, role=self.instructor_role
        )
        Task.objects.create(
            event=self.event, person=self.instructor2, role=self.instructor_role
        )
        Task.objects.create(event=self.event, person=self.host, role=self.host_role)

        # Act
        result = host_instructors_introduction_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        Task.objects.create(
            event=self.event, person=self.instructor1, role=self.instructor_role
        )
        Task.objects.create(
            event=self.event, person=self.instructor2, role=self.instructor_role
        )
        Task.objects.create(event=self.event, person=self.host, role=self.host_role)
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=HOST_INSTRUCTORS_INTRODUCTION_SIGNAL_NAME,
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
        result = host_instructors_introduction_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_remove(self) -> None:
        # Arrange
        Task.objects.create(
            event=self.event, person=self.instructor1, role=self.instructor_role
        )
        Task.objects.create(
            event=self.event, person=self.instructor2, role=self.instructor_role
        )
        # Host Task intentionally not created
        # Task.objects.create(
        #     event=self.event, person=self.host, role=self.host_role
        # )
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=HOST_INSTRUCTORS_INTRODUCTION_SIGNAL_NAME,
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
        result = host_instructors_introduction_strategy(self.event)

        # Assert
        self.assertEqual(result, StrategyEnum.REMOVE)

    def test_strategy_noop(self) -> None:
        # Act
        result = host_instructors_introduction_strategy(self.event)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunHostInstructorsIntroductionStrategy(TestCase):
    @patch(
        "emails.actions.host_instructors_introduction."
        "host_instructors_introduction_signal",
    )
    def test_strategy_calls_create_signal(
        self,
        mock_host_instructors_introduction_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_host_instructors_introduction_strategy(strategy, request, event)

        # Assert
        mock_host_instructors_introduction_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
        )

    @patch(
        "emails.actions.host_instructors_introduction."
        "host_instructors_introduction_update_signal",
    )
    def test_strategy_calls_update_signal(
        self,
        mock_host_instructors_introduction_update_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_host_instructors_introduction_strategy(strategy, request, event)

        # Assert
        mock_host_instructors_introduction_update_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
        )

    @patch(
        "emails.actions.host_instructors_introduction."
        "host_instructors_introduction_remove_signal",
    )
    def test_strategy_calls_remove_signal(
        self,
        mock_host_instructors_introduction_remove_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.REMOVE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_host_instructors_introduction_strategy(strategy, request, event)

        # Assert
        mock_host_instructors_introduction_remove_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
        )

    @patch(
        "emails.actions.host_instructors_introduction.logger",
    )
    @patch(
        "emails.actions.host_instructors_introduction."
        "host_instructors_introduction_signal",
    )
    @patch(
        "emails.actions.host_instructors_introduction."
        "host_instructors_introduction_update_signal",
    )
    @patch(
        "emails.actions.host_instructors_introduction."
        "host_instructors_introduction_remove_signal",
    )
    def test_invalid_strategy_no_signal_called(
        self,
        mock_host_instructors_introduction_remove_signal,
        mock_host_instructors_introduction_update_signal,
        mock_host_instructors_introduction_signal,
        mock_logger,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_host_instructors_introduction_strategy(strategy, request, event)

        # Assert
        mock_host_instructors_introduction_signal.send.assert_not_called()
        mock_host_instructors_introduction_update_signal.send.assert_not_called()
        mock_host_instructors_introduction_remove_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(
            f"Strategy {strategy} for {event} is a no-op"
        )

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act & Assert
        with self.assertRaises(
            EmailStrategyException, msg=f"Unknown strategy {strategy}"
        ):
            run_host_instructors_introduction_strategy(strategy, request, event)
