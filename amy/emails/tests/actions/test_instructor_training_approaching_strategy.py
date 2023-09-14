from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from emails.actions.instructor_training_approaching import (
    instructor_training_approaching_strategy,
    run_instructor_training_approaching_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail
from emails.signals import instructor_training_approaching_signal
from emails.types import StrategyEnum
from workshops.models import Event, Organization, Person, Role, Tag, Task


class TestInstructorTrainingApproachingStrategy(TestCase):
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

    def test_strategy_create(self) -> None:
        # Arrange
        Task.objects.create(
            event=self.event, person=self.instructor1, role=self.instructor_role
        )
        Task.objects.create(
            event=self.event, person=self.instructor2, role=self.instructor_role
        )

        # Act
        result = instructor_training_approaching_strategy(self.event)
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
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_training_approaching_signal.signal_name,
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
            state="scheduled",
            generic_relation=self.event,
        )

        # Act
        result = instructor_training_approaching_strategy(self.event)
        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_remove(self) -> None:
        # Arrange
        Task.objects.create(
            event=self.event, person=self.instructor1, role=self.instructor_role
        )
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_training_approaching_signal.signal_name,
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
            state="scheduled",
            generic_relation=self.event,
        )

        # Act
        result = instructor_training_approaching_strategy(self.event)
        # Assert
        self.assertEqual(result, StrategyEnum.REMOVE)

    def test_strategy_noop(self) -> None:
        # Act
        result = instructor_training_approaching_strategy(self.event)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunInstructorTrainingApproachingStrategy(TestCase):
    @patch(
        "emails.actions.instructor_training_approaching."
        "instructor_training_approaching_signal",
    )
    def test_strategy_calls_create_signal(
        self,
        mock_instructor_training_approaching_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_instructor_training_approaching_strategy(strategy, request, event)

        # Assert
        mock_instructor_training_approaching_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

    @patch(
        "emails.actions.instructor_training_approaching."
        "instructor_training_approaching_update_signal",
    )
    def test_strategy_calls_update_signal(
        self,
        mock_instructor_training_approaching_update_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_instructor_training_approaching_strategy(strategy, request, event)

        # Assert
        mock_instructor_training_approaching_update_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

    @patch(
        "emails.actions.instructor_training_approaching."
        "instructor_training_approaching_remove_signal",
    )
    def test_strategy_calls_remove_signal(
        self,
        mock_instructor_training_approaching_remove_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.REMOVE
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_instructor_training_approaching_strategy(strategy, request, event)

        # Assert
        mock_instructor_training_approaching_remove_signal.send.assert_called_once_with(
            sender=event,
            request=request,
            event=event,
            event_start_date=event.start,
        )

    @patch(
        "emails.actions.instructor_training_approaching."
        "instructor_training_approaching_signal",
    )
    @patch(
        "emails.actions.instructor_training_approaching."
        "instructor_training_approaching_update_signal",
    )
    @patch(
        "emails.actions.instructor_training_approaching."
        "instructor_training_approaching_remove_signal",
    )
    def test_invalid_strategy_no_signal_called(
        self,
        mock_instructor_training_approaching_remove_signal,
        mock_instructor_training_approaching_update_signal,
        mock_instructor_training_approaching_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        event = Event(start=datetime.today())

        # Act
        run_instructor_training_approaching_strategy(strategy, request, event)

        # Assert
        mock_instructor_training_approaching_signal.send.assert_not_called()
        mock_instructor_training_approaching_update_signal.send.assert_not_called()
        mock_instructor_training_approaching_remove_signal.send.assert_not_called()
