from datetime import date

from django.test import TestCase

from fiscal.forms import PartnershipExtensionForm
from fiscal.models import Partnership
from offering.models import Account
from workshops.models import Organization


class TestPartnershipExtensionForm(TestCase):
    def setUp(self) -> None:
        organisation = Organization.objects.create(fullname="test", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        self.partnership = Partnership.objects.create(
            name="Test",
            credits=10,
            account=account,
            agreement_start=date(2025, 10, 25),
            agreement_end=date(2026, 10, 24),
            partner_organisation=organisation,
        )

    def test_clean__error(self) -> None:
        dates = [
            date(2026, 1, 1),
            date(2026, 10, 24),
        ]

        for new_agreement_date in dates:
            with self.subTest(date=new_agreement_date):
                # Arrange
                initial = {
                    "agreement_start": self.partnership.agreement_start,
                    "agreement_end": self.partnership.agreement_end,
                    "extension": 0,
                    "new_agreement_end": self.partnership.agreement_end,
                }
                data = {
                    "agreement_start": self.partnership.agreement_start,
                    "agreement_end": self.partnership.agreement_end,
                    "new_agreement_end": new_agreement_date,
                }

                # Act
                form = PartnershipExtensionForm(data, initial=initial)

                # Assert
                self.assertFalse(form.is_valid())
                self.assertIn("new_agreement_end", form.errors)
                self.assertEqual(
                    form.errors["new_agreement_end"],
                    ["New agreement end date must be later than original agreement end date."],
                )

    def test_clean(self) -> None:
        # Arrange
        initial = {
            "agreement_start": self.partnership.agreement_start,
            "agreement_end": self.partnership.agreement_end,
            "extension": 0,
            "new_agreement_end": self.partnership.agreement_end,
        }
        data = {
            "agreement_start": self.partnership.agreement_start,
            "agreement_end": self.partnership.agreement_end,
            "new_agreement_end": date(2026, 10, 25),
        }

        # Act
        form = PartnershipExtensionForm(data, initial=initial)

        # Assert
        self.assertTrue(form.is_valid())
