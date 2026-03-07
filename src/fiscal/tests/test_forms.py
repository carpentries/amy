from datetime import date

from django.test import TestCase

from src.fiscal.forms import MembershipForm, PartnershipExtensionForm, PartnershipForm
from src.fiscal.models import Partnership, PartnershipTier
from src.offering.models import Account, AccountBenefit, Benefit
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

    def test_clean__registration_code_used_by_account_benefit(self) -> None:
        """Test that form is invalid when registration code is already used by an account benefit."""
        # Arrange
        org = Organization.objects.create(fullname="Benefit Org", domain="benefit.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=org,
        )
        benefit = Benefit.objects.create(name="Test Benefit", unit_type="seat", credits=1)
        account_benefit = AccountBenefit.objects.create(
            account=account,
            benefit=benefit,
            registration_code="DUPLICATE123",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            allocation=5,
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
            [f'This registration code is used by account benefit "{account_benefit}".'],
        )

    def test_clean__valid_unique_registration_code(self) -> None:
        """Test that form is valid when registration code is not used by any membership or account benefit."""
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


MEMBERSHIP_BASE_DATA = {
    "name": "Test Membership",
    "consortium": False,
    "public_status": "public",
    "variant": "bronze",
    "agreement_start": date(2025, 1, 1),
    "agreement_end": date(2025, 12, 31),
    "extensions": "",
    "contribution_type": "financial",
    "registration_code": "",
    "agreement_link": "http://example.com/agreement.pdf",
    "workshops_without_admin_fee_per_agreement": "",
    "public_instructor_training_seats": 0,
    "additional_public_instructor_training_seats": 0,
    "inhouse_instructor_training_seats": 0,
    "additional_inhouse_instructor_training_seats": 0,
    "emergency_contact": "",
}


class TestMembershipForm(TestCase):
    def setUp(self) -> None:
        self.organisation = Organization.objects.create(fullname="test", domain="example.com")
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.organisation,
        )
        tier = PartnershipTier.objects.create(name="Gold", credits=10)
        self.partnership = Partnership.objects.create(
            name="Existing Partnership",
            tier=tier,
            credits=10,
            account=self.account,
            agreement_start=date(2025, 1, 1),
            agreement_end=date(2025, 12, 31),
            agreement_link="http://example.com/agreement.pdf",
            registration_code="PARTNER_CODE",
            public_status="public",
            partner_organisation=self.organisation,
        )
        benefit = Benefit.objects.create(name="Test Benefit", unit_type="seat", credits=1)
        self.account_benefit = AccountBenefit.objects.create(
            account=self.account,
            benefit=benefit,
            registration_code="BENEFIT_CODE",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            allocation=5,
        )

    def test_clean__registration_code_used_by_partnership(self) -> None:
        """Form is invalid when the registration code is already used by a partnership."""
        # Arrange
        data = {**MEMBERSHIP_BASE_DATA, "registration_code": "PARTNER_CODE"}

        # Act
        form = MembershipForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertIn("registration_code", form.errors)
        self.assertEqual(
            form.errors["registration_code"],
            [f'This registration code is used by partnership "{self.partnership}".'],
        )

    def test_clean__registration_code_used_by_account_benefit(self) -> None:
        """Form is invalid when the registration code is already used by an account benefit."""
        # Arrange
        data = {**MEMBERSHIP_BASE_DATA, "registration_code": "BENEFIT_CODE"}

        # Act
        form = MembershipForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertIn("registration_code", form.errors)
        self.assertEqual(
            form.errors["registration_code"],
            [f'This registration code is used by account benefit "{self.account_benefit}".'],
        )

    def test_clean__registration_code_unique(self) -> None:
        """Form is valid when the registration code is not used by any partnership or account benefit."""
        # Arrange
        data = {**MEMBERSHIP_BASE_DATA, "registration_code": "UNIQUE_CODE"}

        # Act
        form = MembershipForm(data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_clean__registration_code_empty(self) -> None:
        """Form is valid when registration code is empty (it's optional)."""
        # Arrange
        data = {**MEMBERSHIP_BASE_DATA, "registration_code": ""}

        # Act
        form = MembershipForm(data)

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
