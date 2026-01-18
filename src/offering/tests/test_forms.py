from datetime import date

from django.test import TestCase

from src.fiscal.models import Partnership
from src.offering.forms import AccountBenefitForm, AccountForm
from src.offering.models import Account, Benefit
from src.workshops.models import Organization


class TestAccountForm(TestCase):
    def test_clean__valid(self) -> None:
        # Arrange
        org = Organization.objects.create(fullname="Test Org", domain="example.com")
        data = {
            "account_type": Account.AccountTypeChoices.ORGANISATION,
            "generic_relation_pk": org.pk,
            "active": True,
        }

        # Act
        form = AccountForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__duplicate_account(self) -> None:
        # Arrange
        org = Organization.objects.create(fullname="Test Org", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=org,
        )

        data = {
            "account_type": Account.AccountTypeChoices.ORGANISATION,
            "generic_relation_pk": org.pk,
            "active": True,
        }

        # Act
        form = AccountForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        msg = f'An account for the selected entity already exists: <a href="{account.get_absolute_url()}">account</a>.'
        self.assertIn(msg, form.errors["generic_relation_pk"])


class TestAccountBenefitForm(TestCase):
    def test_fields_disabled(self) -> None:
        # Act
        form = AccountBenefitForm(disable_account=True, disable_partnership=True, disable_dates=True)
        # Assert
        self.assertTrue(form.fields["account"].disabled)
        self.assertTrue(form.fields["partnership"].disabled)
        self.assertTrue(form.fields["start_date"].disabled)
        self.assertTrue(form.fields["end_date"].disabled)

    def test_clean__valid(self) -> None:
        # Arrange
        org = Organization.objects.create(fullname="Test Org", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=org,
        )
        benefit = Benefit.objects.create(
            name="Test Benefit",
            unit_type="seat",
            credits=2,
        )
        data = {
            "account": account.pk,
            "benefit": benefit.pk,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "allocation": 10,
        }

        # Act
        form = AccountBenefitForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__mismatch_account_partnership(self) -> None:
        # Arrange
        org1 = Organization.objects.create(fullname="Test Org", domain="example.com")
        org2 = Organization.objects.create(fullname="Test Org2", domain="example2.com")
        account1 = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=org1,
        )
        account2 = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=org2,
        )
        partnership = Partnership.objects.create(
            name="Test Partnership",
            partner_organisation=org2,
            account=account2,
            agreement_start=date(2025, 1, 1),
            agreement_end=date(2025, 12, 31),
            credits=10,
        )
        benefit = Benefit.objects.create(
            name="Test Benefit",
            unit_type="seat",
            credits=2,
        )
        data = {
            "account": account1.pk,
            "partnership": partnership.pk,
            "benefit": benefit.pk,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "allocation": 10,
        }

        # Act
        form = AccountBenefitForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        msg = "Selected partnership does not belong to the selected account."
        self.assertIn(msg, form.errors["partnership"])

    def test_clean__no_dates(self) -> None:
        # Arrange
        org = Organization.objects.create(fullname="Test Org", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=org,
        )
        benefit = Benefit.objects.create(
            name="Test Benefit",
            unit_type="seat",
            credits=2,
        )
        data = {
            "account": account.pk,
            "benefit": benefit.pk,
            "start_date": "",
            "end_date": "",
            "allocation": 10,
        }

        # Act
        form = AccountBenefitForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertIn("Start date is required.", form.errors["start_date"])
        self.assertIn("End date is required.", form.errors["end_date"])

    def test_clean__end_before_start(self) -> None:
        # Arrange
        org = Organization.objects.create(fullname="Test Org", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=org,
        )
        benefit = Benefit.objects.create(
            name="Test Benefit",
            unit_type="seat",
            credits=2,
        )
        data = {
            "account": account.pk,
            "benefit": benefit.pk,
            "start_date": "2026-01-01",
            "end_date": "2025-12-31",
            "allocation": 10,
        }

        # Act
        form = AccountBenefitForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertIn("End date must not be before start date.", form.errors["end_date"])
