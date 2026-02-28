from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from src.emails.actions.exceptions import EmailStrategyException
from src.emails.actions.instructor_declined_from_workshop import (
    instructor_declined_from_workshop_strategy,
    run_instructor_declined_from_workshop_strategy,
)
from src.emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from src.emails.signals import INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME
from src.emails.types import StrategyEnum
from src.recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from src.workshops.models import Event, Organization, Person, Tag


class TestInstructorDeclinedFromWorkshopStrategy(TestCase):
    def setUp(self) -> None:
        host = Organization.objects.create(domain="test.com", fullname="Test")
        self.event = Event.objects.create(
            slug="test-event",
            host=host,
            administrator=host,
            start=timezone.now().date() + timedelta(days=2),
            end=timezone.now().date() + timedelta(days=3),
        )
        swc_tag = Tag.objects.create(name="SWC")
        self.event.tags.set([swc_tag])
        self.person = Person.objects.create(email="test@example.org")
        self.recruitment = InstructorRecruitment.objects.create(event=self.event, notes="Test notes")
        self.signup = InstructorRecruitmentSignup.objects.create(
            recruitment=self.recruitment, person=self.person, state="d"
        )

    def test_strategy_create(self) -> None:
        # Arrange

        # Act
        result = instructor_declined_from_workshop_strategy(self.signup)

        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
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
            generic_relation=self.signup,
        )

        # Act
        result = instructor_declined_from_workshop_strategy(self.signup)

        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_cancel(self) -> None:
        # Arrange
        self.signup.state = "a"
        self.signup.save()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
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
            generic_relation=self.signup,
        )

        # Act
        result = instructor_declined_from_workshop_strategy(self.signup)

        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)


class TestRunInstructorDeclinedFromWorkshopStrategy(TestCase):
    def setUp(self) -> None:
        host = Organization.objects.create(domain="test.com", fullname="Test")
        self.event = Event.objects.create(slug="test-event", host=host, start=date(2024, 8, 5), end=date(2024, 8, 5))
        self.person = Person.objects.create(email="test@example.org")
        self.recruitment = InstructorRecruitment.objects.create(event=self.event, notes="Test notes")
        self.signup = InstructorRecruitmentSignup.objects.create(recruitment=self.recruitment, person=self.person)

    @patch("src.emails.actions.instructor_declined_from_workshop.instructor_declined_from_workshop_signal")
    def test_strategy_calls_create_signal(
        self,
        mock_instructor_declined_from_workshop_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")

        # Act
        run_instructor_declined_from_workshop_strategy(
            strategy,
            request,
            signup=self.signup,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

        # Assert
        mock_instructor_declined_from_workshop_signal.send.assert_called_once_with(
            sender=self.signup,
            request=request,
            signup=self.signup,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

    @patch("src.emails.actions.instructor_declined_from_workshop.instructor_declined_from_workshop_update_signal")
    def test_strategy_calls_update_signal(
        self,
        mock_update_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")

        # Act
        run_instructor_declined_from_workshop_strategy(
            strategy,
            request,
            signup=self.signup,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

        # Assert
        mock_update_signal.send.assert_called_once_with(
            sender=self.signup,
            request=request,
            signup=self.signup,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

    @patch("src.emails.actions.instructor_declined_from_workshop.instructor_declined_from_workshop_cancel_signal")
    def test_strategy_calls_cancel_signal(
        self,
        mock_cancel_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CANCEL
        request = RequestFactory().get("/")

        # Act
        run_instructor_declined_from_workshop_strategy(
            strategy,
            request,
            signup=self.signup,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

        # Assert
        mock_cancel_signal.send.assert_called_once_with(
            sender=self.signup,
            request=request,
            signup=self.signup,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

    @patch("src.emails.actions.base_strategy.logger")
    @patch("src.emails.actions.instructor_declined_from_workshop.instructor_declined_from_workshop_signal")
    @patch("src.emails.actions.instructor_declined_from_workshop.instructor_declined_from_workshop_update_signal")
    @patch("src.emails.actions.instructor_declined_from_workshop.instructor_declined_from_workshop_cancel_signal")
    def test_invalid_strategy_no_signal_called(
        self,
        mock_instructor_declined_from_workshop_cancel_signal: MagicMock,
        mock_instructor_declined_from_workshop_update_signal: MagicMock,
        mock_instructor_declined_from_workshop_signal: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")

        # Act
        run_instructor_declined_from_workshop_strategy(
            strategy,
            request,
            signup=self.signup,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

        # Assert
        mock_instructor_declined_from_workshop_signal.send.assert_not_called()
        mock_instructor_declined_from_workshop_update_signal.send.assert_not_called()
        mock_instructor_declined_from_workshop_cancel_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(f"Strategy {strategy} for {self.signup} is a no-op")

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")

        # Act & Assert
        with self.assertRaises(EmailStrategyException, msg=f"Unknown strategy {strategy}"):
            run_instructor_declined_from_workshop_strategy(
                strategy,
                request,
                signup=self.signup,
                person_id=self.person.pk,
                event_id=self.event.pk,
                instructor_recruitment_id=self.recruitment.pk,
                instructor_recruitment_signup_id=self.signup.pk,
            )
