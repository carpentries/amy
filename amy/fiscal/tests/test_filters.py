from datetime import date
from unittest.mock import ANY, MagicMock, call

from django.core.exceptions import ValidationError
from django.db.models import F
from django.test import TestCase

from fiscal.models import Membership
from fiscal.filters import MembershipFilter, MembershipTrainingsFilter
from workshops.models import Organization, Member, MemberRole


class TestMembershipFilter(TestCase):
    def setUp(self):
        self.model = Membership

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
        # Assert
        today = date.today()
        qs_mock.filter.assert_called_once_with(
            agreement_start__lte=today, agreement_end__gte=today
        )
        qs_mock.exclude.assert_not_called()

    def test_filter_organization_name(self):
        # Arrange
        filterset = MembershipFilter({})
        name = "organization_name"
        value = "Test"
        organization = Organization.objects.create(fullname=value, domain="example.org")
        membership = Membership.objects.create(
            name=value,
            variant="Bronze",
            agreement_start=date.today(),
            agreement_end=date.today(),
            contribution_type="Financial",
        )
        role = MemberRole.objects.first()
        member = Member.objects.create(
            membership=membership, organization=organization, role=role
        )
        qs = Membership.objects.all()
        # Act
        result = filterset.filters[name].filter(qs, value)
        # Assert
        self.assertQuerysetEqual(result, qs)
