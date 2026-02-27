from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from src.emails.actions.new_partnership_onboarding import (
    get_context,
    get_generic_relation_object,
    get_recipients,
    get_scheduled_at,
)
from src.emails.types import NewPartnershipOnboardingContext
from src.fiscal.models import Partnership, PartnershipTier
from src.offering.models import Account, AccountOwner
from src.workshops.models import Organization, Person


class TestNewPartnershipOnboardingCommonFunctions(TestCase):
    def setUpAccountOwners(self, account: Account, person1: Person, person2: Person) -> list[AccountOwner]:
        owners = AccountOwner.objects.bulk_create(
            [
                AccountOwner(account=account, person=person1, permission_type="owner"),
                AccountOwner(account=account, person=person2, permission_type="programmatic_contact"),
            ]
        )
        return owners

    def setUpContext(self, partnership: Partnership) -> NewPartnershipOnboardingContext:
        return {
            "partnership": partnership,
        }

    @patch("src.emails.actions.new_partnership_onboarding.immediate_action")
    def test_get_scheduled_at__immediately(self, mock_immediate_action: MagicMock) -> None:
        # Arrange
        partner = Organization.objects.create(fullname="Test Org", domain="test.org")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        agreement_start_date = date(2022, 1, 1)
        partnership = Partnership(
            name="Test Partnership",
            credits=100,
            account=account,
            agreement_start=agreement_start_date,
            agreement_end=agreement_start_date,
            agreement_link="https://example.org/agreement",
            partner_organisation=partner,
        )
        mock_immediate_action.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        scheduled_at = get_scheduled_at(partnership=partnership)

        # Assert
        self.assertEqual(scheduled_at, datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC))

    @patch("src.emails.utils.datetime", wraps=datetime)
    @patch("src.emails.actions.new_partnership_onboarding.immediate_action")
    def test_get_scheduled_at__one_month_before_agreement_start(
        self, mock_immediate_action: MagicMock, mock_datetime: MagicMock
    ) -> None:
        # Arrange
        partner = Organization.objects.create(fullname="Test Org2", domain="test2.org")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        agreement_start_date = date(2023, 6, 1)
        partnership = Partnership(
            name="Test Partnership",
            credits=100,
            account=account,
            agreement_start=agreement_start_date,
            agreement_end=agreement_start_date,
            agreement_link="https://example.org/agreement",
            partner_organisation=partner,
        )
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        scheduled_at = get_scheduled_at(partnership=partnership)

        # Assert
        self.assertEqual(scheduled_at, datetime(2023, 5, 2, 12, 0, 0, tzinfo=UTC))

    def test_get_context(self) -> None:
        # Arrange
        partner = Organization.objects.create(fullname="Test Org3", domain="test3.org")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        agreement_start_date = date(2023, 1, 1)
        partnership = Partnership(
            name="Test Partnership",
            credits=100,
            account=account,
            agreement_start=agreement_start_date,
            agreement_end=agreement_start_date,
            agreement_link="https://example.org/agreement",
            partner_organisation=partner,
        )

        # Act
        context = get_context(partnership=partnership)

        # Assert
        self.assertEqual(
            context,
            {
                "partnership": partnership,
            },
        )

    def test_get_generic_relation_object(self) -> None:
        # Arrange
        partner = Organization.objects.create(fullname="Test Org4", domain="test4.org")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        agreement_start_date = date(2023, 1, 1)
        partnership = Partnership(
            name="Test Partnership",
            credits=100,
            account=account,
            agreement_start=agreement_start_date,
            agreement_end=agreement_start_date,
            agreement_link="https://example.org/agreement",
            partner_organisation=partner,
        )

        # Act
        obj = get_generic_relation_object(
            context=self.setUpContext(partnership),
            partnership=partnership,
        )

        # Assert
        self.assertEqual(obj, partnership)

    def test_get_recipients(self) -> None:
        # Arrange
        partner = Organization.objects.create(fullname="Test Org5", domain="test5.org")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        tier = PartnershipTier.objects.create(name="gold", credits=100)
        partnership = Partnership.objects.create(
            name="Test Partnership",
            tier=tier,
            credits=100,
            account=account,
            registration_code="test-recipients-001",
            agreement_start=date(2024, 1, 1),
            agreement_end=date(2024, 12, 31),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=partner,
        )
        person1 = Person.objects.create(username="test1", email="test1@example.org")
        person2 = Person.objects.create(username="test2", email="test2@example.org")
        self.setUpAccountOwners(account, person1, person2)

        # Act
        obj = get_recipients(
            context=self.setUpContext(partnership),
            partnership=partnership,
        )

        # Assert
        self.assertEqual(obj, ["test1@example.org", "test2@example.org"])

    def test_get_recipients__no_owners(self) -> None:
        # Arrange
        partner = Organization.objects.create(fullname="Test Org6", domain="test6.org")
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
            registration_code="test-noowners-001",
            agreement_start=date(2024, 1, 1),
            agreement_end=date(2024, 12, 31),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=partner,
        )
        # no account owners

        # Act
        obj = get_recipients(
            context=self.setUpContext(partnership),
            partnership=partnership,
        )

        # Assert
        self.assertEqual(obj, [])
