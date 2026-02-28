from datetime import date

from django.test import TestCase

from src.fiscal.forms import PartnershipExtensionForm, PartnershipForm
from src.fiscal.models import Partnership, PartnershipTier
from src.offering.models import Account
from src.workshops.models import Membership, Organization


class TestPartnershipForm(TestCase):
    def setUp(self) -> None:
        self.organisation = Organization.objects.create(fullname="test", domain="example.com")
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.organisation,
        )
        self.tier = PartnershipTier.objects.create(name="Gold", credits=10)

    def test_clean__valid_dates(self) -> None:
        """Test that form is valid when agreement_end is after agreement_start."""
        # Arrange
        data = {
            "partner_organisation": self.organisation.pk,
            "name": "Test Partnership",
            "tier": self.tier.pk,
            "agreement_start": date(2025, 1, 1),
            "agreement_end": date(2025, 12, 31),
            "agreement_link": "http://example.com/agreement.pdf",
            "registration_code": "TEST123",
            "public_status": "public",
        }

        # Act
        form = PartnershipForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__agreement_end_before_start(self) -> None:
        """Test that form is invalid when agreement_end is before agreement_start."""
        # Arrange
        data = {
            "partner_organisation": self.organisation.pk,
            "name": "Test Partnership",
            "tier": self.tier.pk,
            "agreement_start": date(2025, 12, 31),
            "agreement_end": date(2025, 1, 1),
            "agreement_link": "http://example.com/agreement.pdf",
            "registration_code": "TEST123",
            "public_status": "public",
        }

        # Act
        form = PartnershipForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertIn("agreement_end", form.errors)
        self.assertEqual(
            form.errors["agreement_end"],
            ["Agreement end date can't be sooner than the start date."],
        )

    def test_clean__agreement_end_equals_start(self) -> None:
        """Test that form is valid when agreement_end equals agreement_start."""
        # Arrange
        data = {
            "partner_organisation": self.organisation.pk,
            "name": "Test Partnership",
            "tier": self.tier.pk,
            "agreement_start": date(2025, 1, 1),
            "agreement_end": date(2025, 1, 1),
            "agreement_link": "http://example.com/agreement.pdf",
            "registration_code": "TEST123",
            "public_status": "public",
        }

        # Act
        form = PartnershipForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__registration_code_used_by_membership(self) -> None:
        """Test that form is invalid when registration code is already used by a membership."""
        # Arrange
        membership = Membership.objects.create(
            name="Test Membership",
            variant="partner",
            agreement_start=date(2025, 1, 1),
            agreement_end=date(2025, 12, 31),
            registration_code="DUPLICATE123",
        )

        data = {
            "partner_organisation": self.organisation.pk,
            "name": "Test Partnership",
            "tier": self.tier.pk,
            "agreement_start": date(2025, 1, 1),
            "agreement_end": date(2025, 12, 31),
            "agreement_link": "http://example.com/agreement.pdf",
            "registration_code": "DUPLICATE123",
            "public_status": "public",
        }

        # Act
        form = PartnershipForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertIn("registration_code", form.errors)
        self.assertEqual(
            form.errors["registration_code"],
            [f'This registration code is used by membership "{membership}".'],
        )

    def test_clean__valid_unique_registration_code(self) -> None:
        """Test that form is valid when registration code is unique and not used by membership."""
        # Arrange
        data = {
            "partner_organisation": self.organisation.pk,
            "name": "Test Partnership",
            "tier": self.tier.pk,
            "agreement_start": date(2025, 1, 1),
            "agreement_end": date(2025, 12, 31),
            "agreement_link": "http://example.com/agreement.pdf",
            "registration_code": "UNIQUE123",
            "public_status": "public",
        }

        # Act
        form = PartnershipForm(data)

        # Assert
        self.assertTrue(form.is_valid())


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
