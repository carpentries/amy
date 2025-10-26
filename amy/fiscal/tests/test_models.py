from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from fiscal.models import Consortium, Partnership
from offering.models import Account, AccountBenefit, Benefit
from workshops.models import Organization


class TestPartnershipManager(TestCase):
    def test_credits_usage_annotation(self) -> None:
        # Arrange
        organisation = Organization.objects.create(fullname="test", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        benefit1 = Benefit.objects.create(name="product1", unit_type="seat", credits=2)
        benefit2 = Benefit.objects.create(name="product2", unit_type="seat", credits=5)
        partnership = Partnership.objects.create(
            name="Test",
            credits=10,
            account=account,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_organisation=organisation,
        )
        AccountBenefit.objects.create(
            account=account,
            partnership=partnership,
            benefit=benefit1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            allocation=3,
        )
        AccountBenefit.objects.create(
            account=account,
            partnership=partnership,
            benefit=benefit2,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            allocation=2,
        )

        # Act
        queryset = Partnership.objects.credits_usage_annotation()

        # Assert
        self.assertEqual(queryset[0].credits_used, 16)


class TestPartnership(TestCase):
    def test_clean__error_organisation(self) -> None:
        # Arrange
        organisation1 = Organization.objects.create(fullname="test1", domain="example1.com")
        organisation2 = Organization.objects.create(fullname="test2", domain="example2.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation1,
        )
        partnership = Partnership(
            name="Test",
            credits=10,
            account=account,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_organisation=organisation2,
        )

        # Act & Assert
        with self.assertRaises(ValidationError) as cm:
            partnership.clean()

        the_exception = cm.exception
        self.assertEqual(
            the_exception.error_dict["account"],
            [ValidationError("Selected account does not point to partner organisation or consortium.")],
        )

    def test_clean__error_consortium(self) -> None:
        # Arrange
        consortium1 = Consortium.objects.create(name="test1")
        consortium2 = Consortium.objects.create(name="test2")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=consortium1,
        )
        partnership = Partnership(
            name="Test",
            credits=10,
            account=account,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_consortium=consortium2,
        )

        # Act & Assert
        with self.assertRaises(ValidationError) as cm:
            partnership.clean()

        the_exception = cm.exception
        self.assertEqual(
            the_exception.error_dict["account"],
            [ValidationError("Selected account does not point to partner organisation or consortium.")],
        )

    def test_clean(self) -> None:
        # Arrange
        organisation1 = Organization.objects.create(fullname="test1", domain="example1.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation1,
        )
        partnership = Partnership.objects.create(
            name="Test",
            credits=10,
            account=account,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_organisation=organisation1,
        )

        # Act & Assert - no exception
        partnership.clean()

    def test_str(self) -> None:
        # Arrange
        consortium = Consortium.objects.create(name="Test")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.CONSORTIUM,
            generic_relation=consortium,
        )
        partnership = Partnership(
            name="Test",
            credits=10,
            account=account,
            agreement_start=date(2025, 10, 1),
            agreement_end=date(2025, 10, 30),
            partner_consortium=consortium,
        )

        # Act
        result = str(partnership)

        # Assert
        self.assertEqual(result, "Test (No Tier) partnership Oct 01 - 30, 2025 (consortium)")
