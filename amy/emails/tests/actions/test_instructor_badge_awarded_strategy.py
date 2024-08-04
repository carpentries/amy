from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.exceptions import EmailStrategyException
from emails.actions.instructor_badge_awarded import (
    instructor_badge_awarded_strategy,
    run_instructor_badge_awarded_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME
from emails.types import StrategyEnum
from workshops.models import Award, Badge, Person


class TestInstructorBadgeAwardedStrategy(TestCase):
    def setUp(self) -> None:
        self.badge = Badge.objects.create(name="instructor")
        self.person = Person.objects.create(email="test@example.org")

    def test_strategy_create(self) -> None:
        # Arrange
        award = Award.objects.create(badge=self.badge, person=self.person)

        # Act
        result = instructor_badge_awarded_strategy(award, award.person)

        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        award = Award.objects.create(badge=self.badge, person=self.person)
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
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
            generic_relation=award.person,
        )

        # Act
        result = instructor_badge_awarded_strategy(award, award.person)

        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_cancel(self) -> None:
        # Arrange
        # Award intentionally not created
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
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
        result = instructor_badge_awarded_strategy(award=None, person=self.person)

        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)


class TestRunInstructorBadgeAwardedStrategy(TestCase):
    def setUp(self) -> None:
        self.badge = Badge.objects.create(name="test")
        self.person = Person.objects.create(username="test")
        self.award = Award.objects.create(person=self.person, badge=self.badge)

    @patch("emails.actions.instructor_badge_awarded.instructor_badge_awarded_signal")
    def test_strategy_calls_create_signal(
        self,
        mock_instructor_badge_awarded_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")

        # Act
        run_instructor_badge_awarded_strategy(
            strategy,
            request,
            self.person,
            award_id=self.award.pk,
            person_id=self.person.pk,
        )

        # Assert
        mock_instructor_badge_awarded_signal.send.assert_called_once_with(
            sender=self.person,
            request=request,
            award_id=self.award.pk,
            person_id=self.person.pk,
        )

    @patch(
        "emails.actions.instructor_badge_awarded.instructor_badge_awarded_update_signal"
    )
    def test_strategy_calls_update_signal(
        self,
        mock_instructor_badge_awarded_update_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")

        # Act
        run_instructor_badge_awarded_strategy(
            strategy,
            request,
            self.person,
            award_id=self.award.pk,
            person_id=self.person.pk,
        )

        # Assert
        mock_instructor_badge_awarded_update_signal.send.assert_called_once_with(
            sender=self.person,
            request=request,
            award_id=self.award.pk,
            person_id=self.person.pk,
        )

    @patch(
        "emails.actions.instructor_badge_awarded.instructor_badge_awarded_cancel_signal"
    )
    def test_strategy_calls_cancel_signal(
        self,
        mock_instructor_badge_awarded_cancel_signal,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CANCEL
        request = RequestFactory().get("/")

        # Act
        run_instructor_badge_awarded_strategy(
            strategy,
            request,
            self.person,
            award_id=self.award.pk,
            person_id=self.person.pk,
        )

        # Assert
        mock_instructor_badge_awarded_cancel_signal.send.assert_called_once_with(
            sender=self.person,
            request=request,
            award_id=self.award.pk,
            person_id=self.person.pk,
        )

    @patch("emails.actions.base_strategy.logger")
    @patch("emails.actions.instructor_badge_awarded.instructor_badge_awarded_signal")
    @patch(
        "emails.actions.instructor_badge_awarded.instructor_badge_awarded_update_signal"
    )
    @patch(
        "emails.actions.instructor_badge_awarded.instructor_badge_awarded_cancel_signal"
    )
    def test_invalid_strategy_no_signal_called(
        self,
        mock_instructor_badge_awarded_cancel_signal,
        mock_instructor_badge_awarded_update_signal,
        mock_instructor_badge_awarded_signal,
        mock_logger,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")

        # Act
        run_instructor_badge_awarded_strategy(
            strategy,
            request,
            self.person,
            award_id=self.award.pk,
            person_id=self.person.pk,
        )

        # Assert
        mock_instructor_badge_awarded_signal.send.assert_not_called()
        mock_instructor_badge_awarded_update_signal.send.assert_not_called()
        mock_instructor_badge_awarded_cancel_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(
            f"Strategy {strategy} for {self.person} is a no-op"
        )

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")

        # Act & Assert
        with self.assertRaises(
            EmailStrategyException, msg=f"Unknown strategy {strategy}"
        ):
            run_instructor_badge_awarded_strategy(
                strategy,
                request,
                self.person,
                award_id=self.award.pk,
                person_id=self.person.pk,
            )
