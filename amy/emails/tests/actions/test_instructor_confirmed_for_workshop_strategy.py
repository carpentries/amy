from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.exceptions import EmailStrategyException
from emails.actions.instructor_confirmed_for_workshop import (
    instructor_confirmed_for_workshop_strategy,
    run_instructor_confirmed_for_workshop_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME
from emails.types import StrategyEnum
from workshops.models import Event, Organization, Person, Role, Tag, Task


class TestInstructorConfirmedForWorkshopStrategy(TestCase):
    def setUp(self) -> None:
        host = Organization.objects.create(domain="test.com", fullname="Test")
        self.event = Event.objects.create(
            slug="test-event",
            host=host,
            administrator=host,
            start=date(2024, 8, 5),
            end=date(2024, 8, 5),
        )
        swc_tag = Tag.objects.create(name="SWC")
        self.event.tags.set([swc_tag])
        self.person = Person.objects.create(email="test@example.org")
        instructor = Role.objects.create(name="instructor")
        self.task = Task.objects.create(
            role=instructor, person=self.person, event=self.event
        )

    def test_strategy_create(self) -> None:
        # Arrange

        # Act
        result = instructor_confirmed_for_workshop_strategy(self.task)

        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
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
            generic_relation=self.person,
        )

        # Act
        result = instructor_confirmed_for_workshop_strategy(self.task)

        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_cancel(self) -> None:
        # Arrange
        self.task.role = Role.objects.create(name="learner")
        self.task.save()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
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
            generic_relation=self.person,
        )

        # Act
        result = instructor_confirmed_for_workshop_strategy(self.task)

        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)


class TestRunInstructorConfirmedForWorkshopStrategy(TestCase):
    def setUp(self) -> None:
        host = Organization.objects.create(domain="test.com", fullname="Test")
        self.event = Event.objects.create(
            slug="test-event", host=host, start=date(2024, 8, 5), end=date(2024, 8, 5)
        )
        self.person = Person.objects.create(email="test@example.org")
        instructor = Role.objects.create(name="instructor")
        self.task = Task.objects.create(
            role=instructor, person=self.person, event=self.event
        )

    @patch(
        "emails.actions.instructor_confirmed_for_workshop."
        "instructor_confirmed_for_workshop_signal"
    )
    def test_strategy_calls_create_signal(
        self,
        mock_instructor_confirmed_for_workshop_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")

        # Act
        run_instructor_confirmed_for_workshop_strategy(
            strategy,
            request,
            task=self.task,
            person_id=self.task.person.pk,
            event_id=self.task.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

        # Assert
        mock_instructor_confirmed_for_workshop_signal.send.assert_called_once_with(
            sender=self.task,
            request=request,
            task=self.task,
            person_id=self.task.person.pk,
            event_id=self.task.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

    @patch(
        "emails.actions.instructor_confirmed_for_workshop."
        "instructor_confirmed_for_workshop_update_signal"
    )
    def test_strategy_calls_update_signal(
        self,
        mock_instructor_confirmed_for_workshop_update_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")

        # Act
        run_instructor_confirmed_for_workshop_strategy(
            strategy,
            request,
            task=self.task,
            person_id=self.task.person.pk,
            event_id=self.task.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

        # Assert
        mock_instructor_confirmed_for_workshop_update_signal.send.assert_called_once_with(  # noqa: E501
            sender=self.task,
            request=request,
            task=self.task,
            person_id=self.task.person.pk,
            event_id=self.task.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

    @patch(
        "emails.actions.instructor_confirmed_for_workshop."
        "instructor_confirmed_for_workshop_cancel_signal"
    )
    def test_strategy_calls_cancel_signal(
        self,
        mock_instructor_confirmed_for_workshop_cancel_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CANCEL
        request = RequestFactory().get("/")

        # Act
        run_instructor_confirmed_for_workshop_strategy(
            strategy,
            request,
            task=self.task,
            person_id=self.task.person.pk,
            event_id=self.task.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

        # Assert
        mock_instructor_confirmed_for_workshop_cancel_signal.send.assert_called_once_with(  # noqa: E501
            sender=self.task,
            request=request,
            task=self.task,
            person_id=self.task.person.pk,
            event_id=self.task.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

    @patch("emails.actions.base_strategy.logger")
    @patch(
        "emails.actions.instructor_confirmed_for_workshop."
        "instructor_confirmed_for_workshop_signal"
    )
    @patch(
        "emails.actions.instructor_confirmed_for_workshop."
        "instructor_confirmed_for_workshop_update_signal"
    )
    @patch(
        "emails.actions.instructor_confirmed_for_workshop."
        "instructor_confirmed_for_workshop_cancel_signal"
    )
    def test_invalid_strategy_no_signal_called(
        self,
        mock_instructor_confirmed_for_workshop_cancel_signal,
        mock_instructor_confirmed_for_workshop_update_signal,
        mock_instructor_confirmed_for_workshop_signal,
        mock_logger,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")

        # Act
        run_instructor_confirmed_for_workshop_strategy(
            strategy,
            request,
            task=self.task,
            person_id=self.task.person.pk,
            event_id=self.task.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

        # Assert
        mock_instructor_confirmed_for_workshop_signal.send.assert_not_called()
        mock_instructor_confirmed_for_workshop_update_signal.send.assert_not_called()
        mock_instructor_confirmed_for_workshop_cancel_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(
            f"Strategy {strategy} for {self.task} is a no-op"
        )

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")

        # Act & Assert
        with self.assertRaises(
            EmailStrategyException, msg=f"Unknown strategy {strategy}"
        ):
            run_instructor_confirmed_for_workshop_strategy(
                strategy,
                request,
                task=self.task,
                person_id=self.task.person.pk,
                event_id=self.task.event.pk,
                instructor_recruitment_id=None,
                instructor_recruitment_signup_id=None,
            )
