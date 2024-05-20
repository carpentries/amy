from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.exceptions import EmailStrategyException
from emails.actions.instructor_training_completed_not_badged import (
    TrainingCompletionDateException,
    find_training_completion_date,
    instructor_training_completed_not_badged_strategy,
    run_instructor_training_completed_not_badged_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME
from emails.types import StrategyEnum
from workshops.models import (
    Event,
    Organization,
    Person,
    TrainingProgress,
    TrainingRequirement,
)


class TestTrainingCompletionDate(TestCase):
    def setUp(self) -> None:
        self.person = Person.objects.create(
            personal="Test", family="Test", email="test@example.com"
        )

    def setUpEvent(
        self, slug: str, start: date | None = None, end: date | None = None
    ) -> Event:
        organization, _ = Organization.objects.get_or_create(
            domain="test.com", defaults={"fullname": "Test"}
        )
        return Event.objects.create(
            slug=slug,
            host=organization,
            start=start,
            end=end,
        )

    def setUpPassedTraining(
        self, person: Person, event: Event | None = None
    ) -> TrainingProgress:
        training_requirement = TrainingRequirement.objects.get(name="Training")
        return TrainingProgress.objects.create(
            trainee=person,
            state="p",
            requirement=training_requirement,
            event=event,
        )

    def test_find_training_completion_date(self) -> None:
        # Arrange
        event = self.setUpEvent(
            slug="test-event", start=date(2023, 10, 28), end=date(2023, 10, 29)
        )
        self.setUpPassedTraining(self.person, event)
        # Act
        result = find_training_completion_date(self.person)

        # Assert
        self.assertEqual(result, event.end)

    def test_find_training_completion_date__no_training(self) -> None:
        # Act & Assert
        with self.assertRaises(TrainingProgress.DoesNotExist):
            find_training_completion_date(self.person)

    def test_find_training_completion_date__multiple_trainings(self) -> None:
        # Arrange
        event1 = self.setUpEvent(
            slug="test-event1", start=date(2023, 10, 28), end=date(2023, 10, 29)
        )
        event2 = self.setUpEvent(
            slug="test-event2", start=date(2023, 11, 4), end=date(2023, 11, 5)
        )
        self.setUpPassedTraining(self.person, event1)
        self.setUpPassedTraining(self.person, event2)
        # Act & Assert
        with self.assertRaises(TrainingProgress.MultipleObjectsReturned):
            find_training_completion_date(self.person)

    def test_find_training_completion_date__no_event(self) -> None:
        # Arrange
        self.setUpPassedTraining(self.person)
        # Act & Assert
        with self.assertRaisesMessage(
            TrainingCompletionDateException,
            "Training progress doesn't have an event.",
        ):
            find_training_completion_date(self.person)

    def test_find_training_completion_date__no_event_end_date(self) -> None:
        # Arrange
        event = self.setUpEvent(slug="test-event", start=date(2023, 10, 28))
        self.setUpPassedTraining(self.person, event)
        # Act & Assert
        with self.assertRaisesMessage(
            TrainingCompletionDateException,
            "Training progress event doesn't have an end date.",
        ):
            find_training_completion_date(self.person)


class TestInstructorTrainingCompletedNotBadgedStrategy(TestCase):
    def setUp(self) -> None:
        self.person = Person.objects.create(
            personal="Test", family="Test", email="test@example.com"
        )
        organization = Organization.objects.create(domain="test.com", fullname="Test")
        self.event = Event.objects.create(
            slug="test-event",
            host=organization,
            start=date(2023, 10, 28),
            end=date(2023, 10, 29),
        )
        self.training_requirement = TrainingRequirement.objects.get(name="Training")

    def setUpPassedTrainingProgress(
        self,
        person: Person,
        requirement: TrainingRequirement,
        event: Event | None = None,
    ) -> TrainingProgress:
        return TrainingProgress.objects.create(
            trainee=person,
            state="p",
            requirement=requirement,
            event=event,
        )

    def setUpScheduledEmail(
        self,
        person: Person,
        signal: str = INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
        state: ScheduledEmailStatus = ScheduledEmailStatus.SCHEDULED,
    ) -> ScheduledEmail:
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        return ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=state,
            generic_relation=person,
        )

    def test_strategy_create(self) -> None:
        # Arrange
        self.setUpPassedTrainingProgress(
            self.person, self.training_requirement, self.event
        )
        # Act
        result = instructor_training_completed_not_badged_strategy(self.person)
        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        self.setUpPassedTrainingProgress(
            self.person, self.training_requirement, self.event
        )
        self.setUpScheduledEmail(self.person)
        # Act
        result = instructor_training_completed_not_badged_strategy(self.person)
        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_remove(self) -> None:
        # Arrange
        self.setUpScheduledEmail(self.person)
        # Act
        result = instructor_training_completed_not_badged_strategy(self.person)
        # Assert
        self.assertEqual(result, StrategyEnum.REMOVE)

    def test_strategy_noop(self) -> None:
        # Act
        result = instructor_training_completed_not_badged_strategy(self.person)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)

    def test_strategy_noop_when_previous_successful_email_exists(self) -> None:
        # Arrange
        self.setUpPassedTrainingProgress(
            self.person, self.training_requirement, self.event
        )
        self.setUpScheduledEmail(self.person, state=ScheduledEmailStatus.SUCCEEDED)
        # Act
        result = instructor_training_completed_not_badged_strategy(self.person)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunInstructorTrainingCompletedNotBadgedStrategy(TestCase):
    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "instructor_training_completed_not_badged_signal",
    )
    def test_strategy_calls_create_signal(
        self,
        mock_instructor_training_completed_not_badged_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = date(2023, 10, 29)

        # Act
        run_instructor_training_completed_not_badged_strategy(
            strategy, request, person, training_completed_date
        )

        # Assert
        mock_instructor_training_completed_not_badged_signal.send.assert_called_once_with(  # noqa: E501
            sender=person,
            request=request,
            person=person,
            training_completed_date=training_completed_date,
        )

    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "instructor_training_completed_not_badged_update_signal",
    )
    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "find_training_completion_date",
    )
    def test_strategy_calls_update_signal(
        self,
        mock_find_training_completion_date: MagicMock,
        mock_instructor_training_completed_not_badged_update_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = None
        # Mock `find_training_completion_date` is needed when
        # `training_completed_date` is not provided.
        mock_find_training_completion_date.return_value = date(2023, 10, 29)

        # Act
        run_instructor_training_completed_not_badged_strategy(
            strategy, request, person, training_completed_date
        )

        # Assert
        mock_instructor_training_completed_not_badged_update_signal.send.assert_called_once_with(  # noqa: E501
            sender=person,
            request=request,
            person=person,
            training_completed_date=mock_find_training_completion_date.return_value,
        )

    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "instructor_training_completed_not_badged_remove_signal",
    )
    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "find_training_completion_date",
    )
    def test_strategy_calls_remove_signal(
        self,
        mock_find_training_completion_date: MagicMock,
        mock_instructor_training_completed_not_badged_remove_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.REMOVE
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = None
        # Mock `find_training_completion_date` is needed when
        # `training_completed_date` is not provided.
        mock_find_training_completion_date.return_value = date(2023, 10, 29)

        # Act
        run_instructor_training_completed_not_badged_strategy(
            strategy, request, person, training_completed_date
        )

        # Assert
        mock_instructor_training_completed_not_badged_remove_signal.send.assert_called_once_with(  # noqa: E501
            sender=person,
            request=request,
            person=person,
            training_completed_date=mock_find_training_completion_date.return_value,
        )

    @patch("emails.actions.base_strategy.logger")
    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "instructor_training_completed_not_badged_signal",
    )
    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "instructor_training_completed_not_badged_update_signal",
    )
    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "instructor_training_completed_not_badged_remove_signal",
    )
    def test_invalid_strategy_no_signal_called(
        self,
        mock_instructor_training_completed_not_badged_remove_signal: MagicMock,
        mock_instructor_training_completed_not_badged_update_signal: MagicMock,
        mock_instructor_training_completed_not_badged_signal: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = date(2023, 10, 29)

        # Act
        run_instructor_training_completed_not_badged_strategy(
            strategy, request, person, training_completed_date
        )

        # Assert
        mock_instructor_training_completed_not_badged_signal.send.assert_not_called()
        mock_instructor_training_completed_not_badged_update_signal.send.assert_not_called()  # noqa: E501
        mock_instructor_training_completed_not_badged_remove_signal.send.assert_not_called()  # noqa: E501
        mock_logger.debug.assert_called_once_with(
            f"Strategy {strategy} for {person} is a no-op"
        )

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = date(2023, 10, 29)

        # Act & Assert
        with self.assertRaisesMessage(
            EmailStrategyException, f"Unknown strategy {strategy}"
        ):
            run_instructor_training_completed_not_badged_strategy(
                strategy, request, person, training_completed_date
            )

    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "find_training_completion_date",
    )
    def test_missing_training_completed_date__multiple_training_progresses(
        self,
        mock_find_training_completion_date: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = None
        mock_find_training_completion_date.side_effect = (
            TrainingProgress.MultipleObjectsReturned
        )

        # Act & Assert
        with self.assertRaisesMessage(
            EmailStrategyException,
            "Unable to determine training completion date. Person "
            "has multiple passed training progresses.",
        ):
            run_instructor_training_completed_not_badged_strategy(
                strategy, request, person, training_completed_date
            )

    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "find_training_completion_date",
    )
    def test_missing_training_completed_date__no_training_progress(
        self,
        mock_find_training_completion_date: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = None
        mock_find_training_completion_date.side_effect = TrainingProgress.DoesNotExist

        # Act & Assert
        with self.assertRaisesMessage(
            EmailStrategyException,
            "Unable to determine training completion date. Person doesn't have "
            "a passed training progress.",
        ):
            run_instructor_training_completed_not_badged_strategy(
                strategy, request, person, training_completed_date
            )

    @patch(
        "emails.actions.instructor_training_completed_not_badged."
        "find_training_completion_date",
    )
    def test_missing_training_completed_date__issue_with_event_or_event_date(
        self,
        mock_find_training_completion_date: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = None
        mock_find_training_completion_date.side_effect = TrainingCompletionDateException

        # Act & Assert
        with self.assertRaisesMessage(
            EmailStrategyException,
            "Unable to determine training completion date. Probably the person has "
            "training progress not linked to an event, or the event doesn't have "
            "an end date.",
        ):
            run_instructor_training_completed_not_badged_strategy(
                strategy, request, person, training_completed_date
            )
