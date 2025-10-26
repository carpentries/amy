from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django_comments.models import Comment

from fiscal.models import Partnership, PartnershipTier
from offering.models import Account, AccountBenefit, Benefit
from workshops.models import Organization
from workshops.tests.base import TestBase


class TestPartnershipCreate(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
        self.partner = Organization.objects.create(fullname="Test", domain="example.org")
        self.partnership_tier = PartnershipTier.objects.create(name="gold", credits=100)
        self.data = {
            "name": "Test Partnership",
            "tier": self.partnership_tier.pk,
            "agreement_start": "2024-01-01",
            "agreement_end": "2024-12-31",
            "agreement_link": "http://example.com/agreement.pdf",
            "registration_code": "TESTCODE123",
            "public_status": "public",
            "partner_organisation": self.partner.pk,
        }

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_creates_account(self) -> None:
        # Arrange
        url = reverse("partnership-create")

        # Act
        self.client.post(url, self.data)

        # Assert
        Partnership.objects.get(name="Test Partnership")
        content_type = ContentType.objects.get_for_model(Organization)
        Account.objects.get(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation_content_type=content_type,
            generic_relation_pk=self.partner.pk,
        )

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_sets_credits_and_account(self) -> None:
        # Arrange
        url = reverse("partnership-create")

        # Act
        self.client.post(url, self.data)

        # Assert
        partnership = Partnership.objects.get(name="Test Partnership")
        content_type = ContentType.objects.get_for_model(Organization)
        account = Account.objects.get(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation_content_type=content_type,
            generic_relation_pk=self.partner.pk,
        )
        self.assertEqual(partnership.account, account)
        self.assertEqual(partnership.credits, self.partnership_tier.credits)


class TestPartnershipExtend(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
        partner = Organization.objects.create(fullname="Test", domain="example.org")
        partnership_tier = PartnershipTier.objects.create(name="gold", credits=100)
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=partner,
        )
        self.partnership = Partnership.objects.create(
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
        self.data = {
            "agreement_start": "2024-01-01",
            "agreement_end": "2024-12-31",
            "extension": 31,
            "new_agreement_end": "2025-01-31",
        }

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_extension_added(self) -> None:
        # Arrange
        url = reverse("partnership-extend", args=[self.partnership.pk])

        # Act
        self.client.post(url, self.data)

        # Assert
        self.partnership.refresh_from_db()
        self.assertEqual(
            self.partnership.agreement_end,
            date(2025, 1, 31),
        )
        self.assertEqual(
            self.partnership.extensions,
            [31],
        )
        comment = Comment.objects.all()[0]
        today = date.today()
        self.assertIn(
            f"Partnership extended by 31 days on {today} (new end date: 2025-01-31).",
            comment.comment,
        )


class TestPartnershipRollOver(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
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
        self.data = {
            "name": "Test Partnership2",
            "tier": partnership_tier.pk,
            "agreement_start": "2024-01-01",
            "agreement_end": "2024-12-31",
            "agreement_link": "http://example.com/agreement.pdf",
            "registration_code": "TESTCODE123123",
            "public_status": "public",
            "partner_organisation": partner.pk,
        }
        self.benefit1 = Benefit.objects.create(
            name="Benefit1",
            description="Description1",
            unit_type="seat",
            credits=10,
        )
        self.benefit2 = Benefit.objects.create(
            name="Benefit2",
            description="Description1",
            unit_type="seat",
            credits=10,
        )

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_rollover_creates_new_partnership(self) -> None:
        # Arrange
        url = reverse("partnership-roll-over", args=[self.partnership1.pk])

        # Act
        self.client.post(url, self.data)

        # Assert
        self.partnership1.refresh_from_db()
        partnership2 = Partnership.objects.get(name="Test Partnership2")
        self.assertEqual(partnership2.rolled_from_partnership, self.partnership1)
        self.assertEqual(self.partnership1.rolled_to_partnership, partnership2)
        self.assertEqual(partnership2.credits, self.partnership1.credits)
        self.assertEqual(partnership2.account, self.partnership1.account)

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_rollover_freezes_old_account_benefits(self) -> None:
        # Arrange
        AccountBenefit.objects.create(
            account=self.partnership1.account,
            partnership=self.partnership1,
            benefit=self.benefit1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            allocation=10,
            frozen=False,
        )
        AccountBenefit.objects.create(
            account=self.partnership1.account,
            partnership=self.partnership1,
            benefit=self.benefit2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            allocation=10,
            frozen=False,
        )
        url = reverse("partnership-roll-over", args=[self.partnership1.pk])

        # Act
        self.client.post(url, self.data)

        # Assert
        self.assertEqual(AccountBenefit.objects.filter(partnership=self.partnership1, frozen=True).count(), 2)
