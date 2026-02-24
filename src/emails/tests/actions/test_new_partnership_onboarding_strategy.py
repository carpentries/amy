from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from src.emails.actions.exceptions import EmailStrategyException
from src.emails.actions.new_partnership_onboarding import (
    new_partnership_onboarding_strategy,
    run_new_partnership_onboarding_strategy,
)
from src.emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from src.emails.signals import NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME
from src.emails.types import StrategyEnum
from src.fiscal.models import Partnership, PartnershipTier
from src.offering.models import Account, AccountOwner
from src.workshops.models import Organization, Person


class TestNewPartnershipOnboardingStrategy(TestCase):
    def setUp(self) -> None:
        self.partner = Organization.objects.create(fullname="Test Org", domain="test.org")
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.partner,
        )
        tier = PartnershipTier.objects.create(name="gold", credits=100)
        self.partnership = Partnership.objects.create(
            name="Test Partnership",
            tier=tier,
            credits=100,
            account=self.account,
            registration_code="test-code-001",
            agreement_start=date(2024, 1, 1),
            agreement_end=date(2024, 12, 31),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=self.partner,
        )
        person = Person.objects.create(username="testperson", email="test@example.org")
        AccountOwner.objects.create(
            account=self.account,
            person=person,
            permission_type="owner",
        )

    def schedule_email(
        self,
        partnership: Partnership,
        signal: str = NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME,
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
            generic_relation=partnership,
        )

    def test_strategy_create(self) -> None:
        # Act
        result = new_partnership_onboarding_strategy(self.partnership)
        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        self.schedule_email(self.partnership)
        # Act
        result = new_partnership_onboarding_strategy(self.partnership)
        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_cancel_because_no_account_owners(self) -> None:
        # Arrange
        self.schedule_email(self.partnership)
        AccountOwner.objects.all().delete()
        # Act
        result = new_partnership_onboarding_strategy(self.partnership)
        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)

    def test_strategy_noop__partnership_not_saved(self) -> None:
        # Act
        partnership = Partnership()
        result = new_partnership_onboarding_strategy(partnership)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)

    def test_strategy_noop__no_account_owners(self) -> None:
        # Arrange
        AccountOwner.objects.all().delete()
        # Act
        result = new_partnership_onboarding_strategy(self.partnership)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunNewPartnershipOnboardingStrategy(TestCase):
    @patch("src.emails.actions.new_partnership_onboarding.new_partnership_onboarding_signal")
    def test_strategy_calls_create_signal(
        self,
        mock_new_partnership_onboarding_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        partnership = Partnership()

        # Act
        run_new_partnership_onboarding_strategy(strategy, request, partnership)

        # Assert
        mock_new_partnership_onboarding_signal.send.assert_called_once_with(
            sender=partnership,
            request=request,
            partnership=partnership,
        )

    @patch("src.emails.actions.new_partnership_onboarding.new_partnership_onboarding_update_signal")
    def test_strategy_calls_update_signal(
        self,
        mock_new_partnership_onboarding_update_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        partner = Organization.objects.create(fullname="Test Org", domain="test-update.org")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        tier = PartnershipTier.objects.create(name="silver", credits=50)
        partnership = Partnership.objects.create(
            name="Test Partnership",
            tier=tier,
            credits=50,
            account=account,
            registration_code="test-update-001",
            agreement_start=date(2024, 1, 1),
            agreement_end=date(2024, 12, 31),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=partner,
        )

        # Act
        run_new_partnership_onboarding_strategy(strategy, request, partnership)

        # Assert
        mock_new_partnership_onboarding_update_signal.send.assert_called_once_with(
            sender=partnership,
            request=request,
            partnership=partnership,
        )

    @patch("src.emails.actions.new_partnership_onboarding.new_partnership_onboarding_cancel_signal")
    def test_strategy_calls_cancel_signal(
        self,
        mock_new_partnership_onboarding_cancel_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CANCEL
        request = RequestFactory().get("/")
        partner = Organization.objects.create(fullname="Test Org", domain="test-cancel.org")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        tier = PartnershipTier.objects.create(name="bronze", credits=25)
        partnership = Partnership.objects.create(
            name="Test Partnership",
            tier=tier,
            credits=25,
            account=account,
            registration_code="test-cancel-001",
            agreement_start=date(2024, 1, 1),
            agreement_end=date(2024, 12, 31),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=partner,
        )

        # Act
        run_new_partnership_onboarding_strategy(strategy, request, partnership)

        # Assert
        mock_new_partnership_onboarding_cancel_signal.send.assert_called_once_with(
            sender=partnership,
            request=request,
            partnership=partnership,
        )

    @patch("src.emails.actions.base_strategy.logger")
    @patch("src.emails.actions.new_partnership_onboarding.new_partnership_onboarding_signal")
    @patch("src.emails.actions.new_partnership_onboarding.new_partnership_onboarding_update_signal")
    @patch("src.emails.actions.new_partnership_onboarding.new_partnership_onboarding_cancel_signal")
    def test_invalid_strategy_no_signal_called(
        self,
        mock_new_partnership_onboarding_cancel_signal: MagicMock,
        mock_new_partnership_onboarding_update_signal: MagicMock,
        mock_new_partnership_onboarding_signal: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        partnership = Partnership()

        # Act
        run_new_partnership_onboarding_strategy(strategy, request, partnership)

        # Assert
        mock_new_partnership_onboarding_signal.send.assert_not_called()
        mock_new_partnership_onboarding_update_signal.send.assert_not_called()
        mock_new_partnership_onboarding_cancel_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(f"Strategy {strategy} for {partnership} is a no-op")

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")
        partnership = Partnership()

        # Act & Assert
        with self.assertRaisesMessage(EmailStrategyException, f"Unknown strategy {strategy}"):
            run_new_partnership_onboarding_strategy(strategy, request, partnership)
