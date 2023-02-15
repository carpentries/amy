from datetime import date
from unittest.mock import ANY, MagicMock, call

from django.core.exceptions import ValidationError
from django.db.models import F
from django.test import TestCase

from fiscal.models import Membership
from fiscal.filters import MembershipFilter, MembershipTrainingsFilter
from workshops.models import Organization, Member, MemberRole


class TestMembershipFilter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = Membership
        # create a test membership with one organization
        cls.organization = Organization.objects.create(
            fullname="Test Organization", domain="example.org"
        )
        cls.membership = Membership.objects.create(
            name="Test Membership",
            variant="Bronze",
            agreement_start=date.today(),
            agreement_end=date.today(),
            contribution_type="Financial",
        )
        role = MemberRole.objects.first()
        cls.member = Member.objects.create(
            membership=cls.membership, organization=cls.organization, role=role
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.member.delete()
        cls.membership.delete()
        cls.organization.delete()

    def test_fields(self):
        # Arrange
        data = {}
        # Act
        filterset = MembershipFilter(data)
        # Assert
        self.assertEqual(
            set(filterset.filters.keys()),
            {
                "organization_name",
                "consortium",
                "public_status",
                "variant",
                "contribution_type",
                "active_only",
                "training_seats_only",
                "nonpositive_remaining_seats_only",
                "order_by",
            },
        )

    def test_filter_active_only(self):
        # Arrange
        qs_mock = MagicMock()
        filterset = MembershipFilter({})
        name = "active_only"
        # Act
        filterset.filters[name].filter(qs_mock, True)
        today = date.today()
        # Assert
        qs_mock.filter.assert_called_once_with(
            agreement_start__lte=today, agreement_end__gte=today
        )
        qs_mock.exclude.assert_not_called()

    def test_filter_organization_name(self):
        # Arrange
        filterset = MembershipFilter({})
        filter_name = "organization_name"
        value = "Test Organization"
        qs = Membership.objects.all()

        # Act
        result = filterset.filters[filter_name].filter(qs, value)
        # Assert
        self.assertQuerysetEqual(result, [self.membership])
