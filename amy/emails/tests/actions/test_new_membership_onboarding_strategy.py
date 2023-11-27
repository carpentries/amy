from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.new_membership_onboarding import (
    EmailStrategyException,
    new_membership_onboarding_strategy,
    run_new_membership_onboarding_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME
from emails.types import StrategyEnum
from workshops.models import Membership


class TestNewMembershipOnboardingStrategy(TestCase):
    def setUp(self) -> None:
        self.membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2022, 1, 1),
            agreement_end=date(2023, 1, 1),
            contribution_type="financial",
        )

    def setUpScheduledEmail(
        self,
        membership: Membership,
        signal: str = NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
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
            generic_relation=membership,
        )

    def rollOverMembership(self, membership: Membership) -> Membership:
        new_membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2023, 1, 1),
            agreement_end=date(2024, 1, 1),
            contribution_type="financial",
        )
        membership.rolled_to_membership = new_membership  # type: ignore
        membership.save()
        return new_membership

    def test_strategy_create(self) -> None:
        # Arrange
        # self.setUpPassedTrainingProgress(
        #     self.person, self.training_requirement, self.event
        # )
        # Act
        result = new_membership_onboarding_strategy(self.membership)
        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        self.setUpScheduledEmail(self.membership)
        # Act
        result = new_membership_onboarding_strategy(self.membership)
        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_remove(self) -> None:
        # Arrange
        new_membership = self.rollOverMembership(self.membership)
        self.setUpScheduledEmail(new_membership)
        # Act
        result = new_membership_onboarding_strategy(new_membership)
        # Assert
        self.assertEqual(result, StrategyEnum.REMOVE)

    def test_strategy_noop__membership_not_saved(self) -> None:
        # Act
        membership = Membership()
        result = new_membership_onboarding_strategy(membership)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)

    def test_strategy_noop__rolled_over_membership(self) -> None:
        # Arrange
        new_membership = self.rollOverMembership(self.membership)
        # Act
        result = new_membership_onboarding_strategy(new_membership)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunNewMembershipOnboardingStrategy(TestCase):
    @patch("emails.actions.new_membership_onboarding.new_membership_onboarding_signal")
    def test_strategy_calls_create_signal(
        self,
        mock_new_membership_onboarding_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        membership = Membership()

        # Act
        run_new_membership_onboarding_strategy(strategy, request, membership)

        # Assert
        mock_new_membership_onboarding_signal.send.assert_called_once_with(
            sender=membership,
            request=request,
            membership=membership,
        )

    @patch(
        "emails.actions.new_membership_onboarding."
        "new_membership_onboarding_update_signal"
    )
    def test_strategy_calls_update_signal(
        self,
        mock_new_membership_onboarding_update_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2022, 1, 1),
            agreement_end=date(2023, 1, 1),
            contribution_type="financial",
        )

        # Act
        run_new_membership_onboarding_strategy(strategy, request, membership)

        # Assert
        mock_new_membership_onboarding_update_signal.send.assert_called_once_with(
            sender=membership,
            request=request,
            membership=membership,
        )

    @patch(
        "emails.actions.new_membership_onboarding."
        "new_membership_onboarding_remove_signal"
    )
    def test_strategy_calls_remove_signal(
        self,
        mock_new_membership_onboarding_remove_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.REMOVE
        request = RequestFactory().get("/")
        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2022, 1, 1),
            agreement_end=date(2023, 1, 1),
            contribution_type="financial",
        )

        # Act
        run_new_membership_onboarding_strategy(strategy, request, membership)

        # Assert
        mock_new_membership_onboarding_remove_signal.send.assert_called_once_with(
            sender=membership,
            request=request,
            membership=membership,
        )

    @patch("emails.actions.new_membership_onboarding.logger")
    @patch("emails.actions.new_membership_onboarding.new_membership_onboarding_signal")
    @patch(
        "emails.actions.new_membership_onboarding."
        "new_membership_onboarding_update_signal"
    )
    @patch(
        "emails.actions.new_membership_onboarding."
        "new_membership_onboarding_remove_signal"
    )
    def test_invalid_strategy_no_signal_called(
        self,
        mock_new_membership_onboarding_remove_signal: MagicMock,
        mock_new_membership_onboarding_update_signal: MagicMock,
        mock_new_membership_onboarding_signal: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        membership = Membership()

        # Act
        run_new_membership_onboarding_strategy(strategy, request, membership)

        # Assert
        mock_new_membership_onboarding_signal.send.assert_not_called()
        mock_new_membership_onboarding_update_signal.send.assert_not_called()
        mock_new_membership_onboarding_remove_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(
            f"Strategy {strategy} for {membership} is a no-op"
        )

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")
        membership = Membership()

        # Act & Assert
        with self.assertRaisesMessage(
            EmailStrategyException, f"Unknown strategy {strategy}"
        ):
            run_new_membership_onboarding_strategy(strategy, request, membership)
