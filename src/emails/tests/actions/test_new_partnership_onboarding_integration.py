from datetime import date, timedelta
from unittest.mock import patch

from django.test import RequestFactory, override_settings
from django.urls import reverse

from src.emails.actions.new_partnership_onboarding import (
    new_partnership_onboarding_strategy,
    run_new_partnership_onboarding_strategy,
)
from src.emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from src.emails.signals import NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME
from src.fiscal.models import Partnership, PartnershipTier
from src.offering.models import Account, AccountOwner
from src.workshops.models import Organization
from src.workshops.tests.base import TestBase


class TestNewPartnershipOnboardingReceiverIntegration(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
        self.partner = Organization.objects.create(fullname="Test Partner Org", domain="partner.org")
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
            registration_code="test-integration-001",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=self.partner,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)], "SERVICE_OFFERING": [("boolean", True)]})
    def test_integration_create_via_account_owners_update(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        url = reverse("account-owners-update", args=[self.account.pk])
        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-account": self.account.pk,
            "form-0-person": self.hermione.pk,
            "form-0-permission_type": "owner",
            "form-0-id": "",
            "form-0-EDITABLE": True,
        }

        # Act
        rv = self.client.post(url, data=data)

        # Assert
        self.assertEqual(rv.status_code, 302)
        scheduled_email = ScheduledEmail.objects.get(template=template)
        self.assertEqual(scheduled_email.to_header, [self.hermione.email])


class TestNewPartnershipOnboardingUpdateReceiverIntegration(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
        self.partner = Organization.objects.create(fullname="Test Partner Org2", domain="partner2.org")
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.partner,
        )
        self.tier = PartnershipTier.objects.create(name="silver", credits=50)
        self.partnership = Partnership.objects.create(
            name="Test Partnership",
            tier=self.tier,
            credits=50,
            account=self.account,
            registration_code="test-update-integration-001",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=self.partner,
        )
        AccountOwner.objects.create(
            account=self.account,
            person=self.hermione,
            permission_type="owner",
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)], "SERVICE_OFFERING": [("boolean", True)]})
    def test_integration_update_via_partnership_edit(self) -> None:
        # Arrange
        signal = NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_new_partnership_onboarding_strategy(
                new_partnership_onboarding_strategy(self.partnership),
                request=request,
                partnership=self.partnership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("partnership-update", args=[self.partnership.pk])
        data = {
            "name": self.partnership.name,
            "tier": self.tier.pk,
            "agreement_start": self.partnership.agreement_start.isoformat(),
            "agreement_end": self.partnership.agreement_end.isoformat(),
            "agreement_link": self.partnership.agreement_link,
            "registration_code": self.partnership.registration_code,
            "public_status": self.partnership.public_status,
            "partner_organisation": self.partner.pk,
        }

        # Act
        rv = self.client.post(url, data=data)

        # Assert
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, f"Updated {signal}")


class TestNewPartnershipOnboardingCancelIntegration(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpUsersAndLogin()
        self.partner = Organization.objects.create(fullname="Test Partner Org3", domain="partner3.org")
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.partner,
        )
        self.tier = PartnershipTier.objects.create(name="bronze", credits=25)
        self.partnership = Partnership.objects.create(
            name="Test Partnership",
            tier=self.tier,
            credits=25,
            account=self.account,
            registration_code="test-cancel-integration-001",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            agreement_link="https://example.org/agreement",
            public_status="public",
            partner_organisation=self.partner,
        )
        self.owner = AccountOwner.objects.create(
            account=self.account,
            person=self.hermione,
            permission_type="owner",
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)], "SERVICE_OFFERING": [("boolean", True)]})
    def test_integration_cancel_via_partnership_delete(self) -> None:
        # Arrange
        signal = NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_new_partnership_onboarding_strategy(
                new_partnership_onboarding_strategy(self.partnership),
                request=request,
                partnership=self.partnership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("partnership-delete", args=[self.partnership.pk])

        # Act
        rv = self.client.post(url)

        # Assert
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, "Email was cancelled")

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)], "SERVICE_OFFERING": [("boolean", True)]})
    def test_integration_cancel_via_account_owners_update(self) -> None:
        # Arrange
        signal = NEW_PARTNERSHIP_ONBOARDING_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_new_partnership_onboarding_strategy(
                new_partnership_onboarding_strategy(self.partnership),
                request=request,
                partnership=self.partnership,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("account-owners-update", args=[self.account.pk])
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-account": self.account.pk,
            "form-0-person": self.owner.person.pk,
            "form-0-permission_type": self.owner.permission_type,
            "form-0-id": self.owner.pk,
            "form-0-DELETE": "on",
        }

        # Act
        rv = self.client.post(url, data=data)

        # Assert
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(AccountOwner.objects.filter(account=self.account).count(), 0)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, "Email was cancelled")
