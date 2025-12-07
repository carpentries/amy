from datetime import date

from django.test import TestCase

from fiscal.models import Partnership, PartnershipTier
from offering.models import Account, AccountBenefit, Benefit
from workshops.models import Event, Organization, Person, Role, Task


class TestAccountBenefit(TestCase):
    def setUp(self) -> None:
        partner = Organization.objects.create(fullname="Test", domain="example.org")
        partnership_tier = PartnershipTier.objects.create(name="gold", credits=100)
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        self.partnership1 = Partnership.objects.create(
            name="Test Partnership",
            tier=partnership_tier,
            agreement_start=date(2024, 1, 1),
            agreement_end=date(2024, 12, 31),
            agreement_link="http://example.com/agreement.pdf",
            registration_code="TESTCODE123",
            public_status="public",
            partner_organisation=partner,
            credits=100,
            account=account,
        )
        self.benefit1 = Benefit.objects.create(
            name="Benefit1",
            description="Description1",
            unit_type="seat",
            credits=10,
        )

    def test_human_daterange(self) -> None:
        # Arrange
        account_benefit = AccountBenefit.objects.create(
            account=self.partnership1.account,
            partnership=self.partnership1,
            benefit=self.benefit1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            allocation=10,
            frozen=False,
        )

        # Act
        human_range = account_benefit.human_daterange

        # Assert
        self.assertEqual(human_range, "Jan 01 - Dec 31, 2024")

    def test_active(self) -> None:
        # Arrange
        account_benefit = AccountBenefit.objects.create(
            account=self.partnership1.account,
            partnership=self.partnership1,
            benefit=self.benefit1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            allocation=10,
            frozen=False,
        )

        # Act & Assert
        self.assertTrue(account_benefit.active(current_date=date(2024, 6, 15)))
        self.assertFalse(account_benefit.active(current_date=date(2025, 1, 1)))

    def test_str(self) -> None:
        # Arrange
        account_benefit = AccountBenefit.objects.create(
            account=self.partnership1.account,
            partnership=self.partnership1,
            benefit=self.benefit1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            allocation=10,
            frozen=True,
        )

        # Act
        benefit_str = str(account_benefit)

        # Assert
        expected_str = (
            '(FROZEN) Account Benefit "Benefit1" (seat, 10 credits) for '
            '"Test Partnership Gold partnership Jan 01 - Dec 31, 2024"'
            " (allocation: 10, valid: Jan 01 - Dec 31, 2024)"
        )
        self.assertEqual(benefit_str, expected_str)

    def test_allocation_used(self) -> None:
        # Arrange
        account_benefit = AccountBenefit.objects.create(
            account=self.partnership1.account,
            partnership=self.partnership1,
            benefit=self.benefit1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            allocation=10,
            frozen=False,
        )
        Task.objects.create(
            allocated_benefit=account_benefit,
            event=Event.objects.create(slug="test-event", host=Organization.objects.all()[0]),
            person=Person.objects.create(personal="Test", family="User", email="test@test.com"),
            role=Role.objects.create(name="learner"),
        )

        # Act
        used_allocation = account_benefit.allocation_used()

        # Assert
        self.assertEqual(used_allocation, 1)
