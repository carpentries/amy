from datetime import date

from django.test import RequestFactory, TestCase
from django.views.generic.base import ContextMixin, View

from fiscal.base_views import GetPartnershipMixin
from fiscal.models import Partnership
from offering.models import Account
from workshops.models import Organization


class TestGetPartnershipMixin(TestCase):
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
            agreement_start=date(2025, 10, 24),
            agreement_end=date(2026, 10, 23),
            partner_organisation=organisation,
        )

    def test_no_pk_kwarg(self) -> None:
        # Arrange
        class TestView(GetPartnershipMixin, View):
            pass

        request = RequestFactory().get("/")
        v = TestView()
        v.setup(request)  # no `pk` keyword argument

        # Act & Assert
        with self.assertRaises(KeyError):
            v.dispatch(request)

    def test_with_pk_kwarg(self) -> None:
        # Arrange
        class TestView(GetPartnershipMixin, View):
            pass

        request = RequestFactory().get("/")
        v = TestView()
        v.setup(request, pk=self.partnership.pk)

        # Act
        v.dispatch(request)

        # Assert
        self.assertEqual(v.partnership, self.partnership)

    def test_context_data(self) -> None:
        # Arrange
        class TestView(GetPartnershipMixin, ContextMixin, View):
            pass

        request = RequestFactory().get("/")
        v = TestView()
        v.setup(request, pk=self.partnership.pk)

        # Act
        v.dispatch(request)
        result = v.get_context_data()

        # Assert
        self.assertEqual(result["partnership"], self.partnership)
