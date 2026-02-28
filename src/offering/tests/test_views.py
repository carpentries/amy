from datetime import date

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from src.fiscal.models import Partnership
from src.offering.models import Account, AccountOwner
from src.offering.views import AccountBenefitCreate
from src.workshops.models import Organization, Person
from src.workshops.tests.base import TestBase


class TestAccountCreateView(TestBase):
    """Tests for AccountCreate logic of creating account owner when account for individual is created."""

    def setUp(self) -> None:
        super().setUp()
        self._setUpSuperuser()
        self._logSuperuserIn()

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_form_valid_creates_account_with_correct_content_type_individual(self) -> None:
        """Test that account is created with correct content type for individual account."""
        # Arrange
        person = Person.objects.create(personal="John", family="Doe", email="john@example.com")
        payload = {
            "account_type": Account.AccountTypeChoices.INDIVIDUAL,
            "generic_relation_pk": person.pk,
            "active": True,
        }

        # Act
        result = self.client.post(reverse("account-create"), payload, follow=True)

        # Assert
        self.assertEqual(result.status_code, 200)
        AccountOwner.objects.get(person=person)


class TestAccountUpdateView(TestBase):
    """Tests for AccountUpdate logic of updating account owner when account for individual is updated."""

    def setUp(self) -> None:
        super().setUp()
        self._setUpSuperuser()
        self._logSuperuserIn()

        self.person1 = Person.objects.create(personal="John", family="Doe", email="john@example.com")
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.INDIVIDUAL,
            generic_relation=self.person1,
        )

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_form_valid_creates_account_with_correct_content_type_individual(self) -> None:
        """Test that account is created with correct content type for individual account."""
        # Arrange
        person2 = Person.objects.create(username="test")
        payload = {
            "account_type": Account.AccountTypeChoices.INDIVIDUAL,
            "generic_relation_pk": person2.pk,
            "active": True,
        }

        # Act
        result = self.client.post(reverse("account-update", args=(self.account.pk,)), payload, follow=True)

        # Assert
        self.assertEqual(result.status_code, 200)
        account_owner = AccountOwner.objects.get(account=self.account)
        self.assertEqual(account_owner.person, person2)


class TestAccountOwnersUpdateView(TestBase):
    """Tests for AccountOwnersUpdate not loading in for individual account."""

    def setUp(self) -> None:
        super().setUp()
        self._setUpSuperuser()
        self._logSuperuserIn()

        person = Person.objects.create(personal="John", family="Doe", email="john@example.com")
        self.account1 = Account.objects.create(
            account_type=Account.AccountTypeChoices.INDIVIDUAL,
            generic_relation=person,
        )
        organisation = Organization.objects.create(fullname="test", domain="example.com")
        self.account2 = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_form_inaccessible_for_account_individual(self) -> None:
        """Test that form is not accessible for individual account."""
        # Act
        result = self.client.get(reverse("account-owners-update", args=(self.account1.pk,)))

        # Assert
        self.assertEqual(result.status_code, 404)

    @override_settings(FLAGS={"SERVICE_OFFERING": [("boolean", True)]})
    def test_form_accessible_for_account_organisation(self) -> None:
        """Test that form is accessible for account for organisation."""
        # Act
        result = self.client.get(reverse("account-owners-update", args=(self.account2.pk,)))

        # Assert
        self.assertEqual(result.status_code, 200)


class TestAccountBenefitCreateView(TestCase):
    def test_get_initial(self) -> None:
        # Arrange
        organisation = Organization.objects.create(fullname="test", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        partnership = Partnership.objects.create(
            name="Test Partnership",
            credits=10,
            account=account,
            agreement_start=date(2025, 10, 24),
            agreement_end=date(2026, 10, 23),
            partner_organisation=organisation,
        )
        request = RequestFactory().get(
            "/",
            query_params={
                "account_pk": account.pk,
                "partnership_pk": partnership.pk,
            },
        )

        # Act
        view = AccountBenefitCreate(request=request)
        result = view.get_initial()

        # Assert
        self.assertEqual(
            result,
            {
                "start_date": partnership.agreement_start,
                "end_date": partnership.agreement_end,
                "account": account,
                "partnership": partnership,
            },
        )

    def test_get_form_kwargs(self) -> None:
        # Arrange
        organisation = Organization.objects.create(fullname="test", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        partnership = Partnership.objects.create(
            name="Test Partnership",
            credits=10,
            account=account,
            agreement_start=date(2025, 10, 24),
            agreement_end=date(2026, 10, 23),
            partner_organisation=organisation,
        )
        request = RequestFactory().get(
            "/",
            query_params={
                "account_pk": account.pk,
                "partnership_pk": partnership.pk,
            },
        )

        # Act
        view = AccountBenefitCreate(request=request)
        result = view.get_form_kwargs()

        # Assert - partial dict equality
        self.assertTrue(result["disable_account"])
        self.assertTrue(result["disable_partnership"])
        self.assertTrue(result["disable_dates"])
