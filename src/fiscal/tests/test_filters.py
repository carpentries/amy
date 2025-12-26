from datetime import date, timedelta

from django.test import TestCase

from src.fiscal.filters import (
    MembershipFilter,
    MembershipTrainingsFilter,
    filter_consortium_organisation_contain,
    filter_currently_active_partnership,
    filter_partnership_credits,
)
from src.fiscal.models import Consortium, Partnership
from src.offering.models import Account, AccountBenefit, Benefit
from src.workshops.models import (
    Event,
    Member,
    MemberRole,
    Membership,
    Organization,
    Role,
    Task,
)
from src.workshops.tests.base import TestBase


class TestMembershipFilter(TestBase):
    """
    A test should exist for each filter listed in test_fields().
    """

    def setUp(self) -> None:
        super().setUp()  # create some organizations and persons
        self._setUpRoles()  # create the learner role

        self.model = Membership
        member_role = MemberRole.objects.all()[0]

        self.membership = Membership.objects.create(
            name="Test Membership",
            variant="Bronze",
            agreement_start=date.today(),
            agreement_end=date.today(),
            contribution_type="Financial",
            public_instructor_training_seats=1,
            consortium=True,
            public_status="public",
        )
        self.member = Member.objects.create(membership=self.membership, organization=self.org_alpha, role=member_role)
        self.membership2 = Membership.objects.create(
            name="To Be Filtered Out",
            variant="Silver",
            agreement_start=date(2015, 1, 1),
            agreement_end=date(2016, 1, 1),
            contribution_type="Person-days",
            public_instructor_training_seats=0,
            consortium=False,
            public_status="private",
        )
        self.member2 = Member.objects.create(
            membership=self.membership2,
            organization=self.org_beta,
            role=member_role,
        )
        self.qs = Membership.objects.annotate_with_seat_usage()

        # create 2 used seats on test membership
        # will make remaining seats negative
        self.event = Event.objects.create(
            host=self.org_alpha,
            sponsor=self.org_alpha,
            membership=self.membership,
            slug="2023-02-16-ttt-test",
        )
        role_learner = Role.objects.get(name="learner")
        self.task = Task.objects.create(
            event=self.event,
            person=self.ironman,
            role=role_learner,
            seat_membership=self.membership,
            seat_public=True,
        )
        self.task2 = Task.objects.create(
            event=self.event,
            person=self.blackwidow,
            role=role_learner,
            seat_membership=self.membership,
            seat_public=True,
        )

        # get filterset
        self.filterset = MembershipFilter({})

    def tearDown(self) -> None:
        # clean up used seats
        self.task.delete()
        self.task2.delete()
        self.event.delete()

        # clean up memberships
        self.member.delete()
        self.membership.delete()
        self.member2.delete()
        self.membership2.delete()

        super().tearDown()

    def test_fields(self) -> None:
        # Arrange & Act stages happen in setUp()
        # Assert
        self.assertEqual(
            set(self.filterset.filters.keys()),
            {
                "organization_name",
                "consortium",
                "public_status",
                "variant",
                "contribution_type",
                "active_only",
                "training_seats_only",
                "negative_remaining_seats_only",
                "order_by",
            },
        )

    def test_filter_organization_name(self) -> None:
        # Arrange
        filter_name = "organization_name"
        value = "Alpha Organization"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerySetEqual(result, [self.membership])

    def test_filter_consortium(self) -> None:
        # Arrange
        filter_name = "consortium"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerySetEqual(result, [self.membership])

    def test_filter_public_status(self) -> None:
        # Arrange
        filter_name = "public_status"
        value = "public"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerySetEqual(result, [self.membership])

    def test_filter_variant(self) -> None:
        # Arrange
        filter_name = "variant"
        value = "Bronze"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_contribution_type(self) -> None:
        # Arrange
        filter_name = "contribution_type"
        value = "Financial"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_active_only(self) -> None:
        # Arrange
        name = "active_only"
        value = True

        # Act
        result = self.filterset.filters[name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_training_seats_only(self) -> None:
        # Arrange
        filter_name = "training_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_negative_remaining_seats_only(self) -> None:
        # Arrange
        filter_name = "negative_remaining_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_order_by(self) -> None:
        # Arrange
        filter_name = "order_by"
        fields = self.filterset.filters[filter_name].param_map
        results = {}
        # default ordering is ascending
        expected_results = {
            "agreement_start": [self.membership2, self.membership],
            "agreement_end": [self.membership2, self.membership],
            "instructor_training_seats_remaining": [self.membership, self.membership2],
        }

        # Act
        for field in fields:
            results[field] = self.filterset.filters[filter_name].filter(self.qs, [field])

        # Assert
        # we don't have any unexpected fields
        self.assertEqual(fields.keys(), expected_results.keys())
        # each field was filtered correctly
        for field in fields:
            self.assertQuerySetEqual(results[field], expected_results[field])


class TestMembershipTrainingsFilter(TestBase):
    """
    A test should exist for each filter listed in test_fields().
    There is overlap in filters between MembershipFilter and MembershipTrainingsFilter,
    so tests have been duplicated from TestMembershipFilter where possible.
    """

    def setUp(self) -> None:
        super().setUp()  # create some organizations and persons
        self._setUpRoles()  # create the learner role

        self.model = Membership
        member_role = MemberRole.objects.all()[0]

        self.membership = Membership.objects.create(
            name="Test Membership",
            variant="Bronze",
            agreement_start=date.today(),
            agreement_end=date.today(),
            contribution_type="Financial",
            public_instructor_training_seats=1,
        )
        self.member = Member.objects.create(membership=self.membership, organization=self.org_alpha, role=member_role)
        self.membership2 = Membership.objects.create(
            name="To Be Filtered Out",
            variant="Silver",
            agreement_start=date(2015, 1, 1),
            agreement_end=date(2016, 1, 1),
            contribution_type="Person-days",
            public_instructor_training_seats=0,
        )
        self.member2 = Member.objects.create(
            membership=self.membership2,
            organization=self.org_beta,
            role=member_role,
        )
        self.qs = Membership.objects.annotate_with_seat_usage()

        # create 2 used seats on test membership
        # will make remaining seats negative
        self.event = Event.objects.create(
            host=self.org_alpha,
            sponsor=self.org_alpha,
            membership=self.membership,
            slug="2023-02-16-ttt-test",
        )
        role_learner = Role.objects.get(name="learner")
        self.task = Task.objects.create(
            event=self.event,
            person=self.ironman,
            role=role_learner,
            seat_membership=self.membership,
            seat_public=True,
        )
        self.task2 = Task.objects.create(
            event=self.event,
            person=self.blackwidow,
            role=role_learner,
            seat_membership=self.membership,
            seat_public=True,
        )

        # get filterset
        self.filterset = MembershipTrainingsFilter({})

    def tearDown(self) -> None:
        # clean up used seats
        self.task.delete()
        self.task2.delete()
        self.event.delete()

        # clean up memberships
        self.member.delete()
        self.membership.delete()
        self.member2.delete()
        self.membership2.delete()

        super().tearDown()

    def test_fields(self) -> None:
        # Arrange & Act stages happen in setUp()
        # Assert
        self.assertEqual(
            set(self.filterset.filters.keys()),
            {
                "organization_name",
                "active_only",
                "training_seats_only",
                "negative_remaining_seats_only",
                "order_by",
            },
        )

    def test_filter_organization_name(self) -> None:
        # Arrange
        filter_name = "organization_name"
        value = "Alpha Organization"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerySetEqual(result, [self.membership])

    def test_filter_active_only(self) -> None:
        # Arrange
        name = "active_only"
        value = True

        # Act
        result = self.filterset.filters[name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_training_seats_only(self) -> None:
        # Arrange
        filter_name = "training_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_negative_remaining_seats_only(self) -> None:
        # Arrange
        filter_name = "negative_remaining_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.membership, result)
        self.assertNotIn(self.membership2, result)

    def test_filter_order_by(self) -> None:
        # Arrange
        filter_name = "order_by"
        fields = self.filterset.filters[filter_name].param_map
        results = {}
        # default ordering is ascending
        expected_results = {
            "name": [self.membership, self.membership2],
            "agreement_start": [self.membership2, self.membership],
            "agreement_end": [self.membership2, self.membership],
            "instructor_training_seats_total": [self.membership2, self.membership],
            "instructor_training_seats_utilized": [self.membership2, self.membership],
            "instructor_training_seats_remaining": [self.membership, self.membership2],
        }

        # Act
        for field in fields:
            results[field] = self.filterset.filters[filter_name].filter(self.qs, [field])

        # Assert
        # we don't have any unexpected fields
        self.assertEqual(fields.keys(), expected_results.keys())
        # each field was filtered correctly
        for field in fields:
            self.assertQuerySetEqual(results[field], expected_results[field])


class TestConsortiumFilterMethods(TestCase):
    def test_filter_consortium_organisation_contain__no_filter(self) -> None:
        # Arrange
        swc = Organization.objects.create(domain="software-carpentry.org")
        consortium = Consortium.objects.create(name="test-consortium")
        consortium.organisations.add(swc)
        queryset = Consortium.objects.all()
        organizations: list[Organization] = []

        # Act
        qs = filter_consortium_organisation_contain(queryset, "", organizations)

        # Assert
        self.assertQuerySetEqual(qs, list(queryset))

    def test_filter_consortium_organisation_contain__filter(self) -> None:
        # Arrange
        swc = Organization.objects.create(domain="software-carpentry.org")
        consortium = Consortium.objects.create(name="test-consortium")
        consortium.organisations.add(swc)
        queryset = Consortium.objects.all()
        organizations = [swc]

        # Act
        qs = filter_consortium_organisation_contain(queryset, "", organizations)

        # Assert
        self.assertQuerySetEqual(qs, [consortium])


class TestPartnershipFilterMethods(TestCase):
    def test_filter_currently_active_partnership__no_filter(self) -> None:
        # Arrange
        organisation = Organization.objects.create(fullname="test", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        partnership1 = Partnership.objects.create(
            name="Test1",
            credits=10,
            account=account,
            agreement_start=date(2020, 10, 24),
            agreement_end=date(2021, 10, 23),
            partner_organisation=organisation,
        )
        partnership2 = Partnership.objects.create(
            name="Test2",
            credits=10,
            account=account,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_organisation=organisation,
        )
        queryset = Partnership.objects.all()
        # Act
        qs = filter_currently_active_partnership(queryset, "", active=False)
        # Assert
        self.assertQuerySetEqual(qs, {partnership1, partnership2}, ordered=False)

    def test_filter_currently_active_partnership__filter(self) -> None:
        # Arrange
        organisation = Organization.objects.create(fullname="test", domain="example.com")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation,
        )
        _ = Partnership.objects.create(
            name="Test1",
            credits=10,
            account=account,
            agreement_start=date(2020, 10, 24),
            agreement_end=date(2021, 10, 23),
            partner_organisation=organisation,
        )
        partnership2 = Partnership.objects.create(
            name="Test2",
            credits=10,
            account=account,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_organisation=organisation,
        )
        queryset = Partnership.objects.all()
        # Act
        qs = filter_currently_active_partnership(queryset, "", active=True)
        # Assert
        self.assertQuerySetEqual(qs, [partnership2])

    def test_filter_partnership_credits(self) -> None:
        # Arrange
        organisation1 = Organization.objects.create(fullname="test1", domain="example1.com")
        organisation2 = Organization.objects.create(fullname="test2", domain="example2.com")
        account1 = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation1,
        )
        account2 = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=organisation2,
        )
        benefit = Benefit.objects.create(name="product", unit_type="seat", credits=6)
        partnership1 = Partnership.objects.create(
            name="Test1",
            credits=10,
            account=account1,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_organisation=organisation1,
        )
        partnership2 = Partnership.objects.create(
            name="Test2",
            credits=10,
            account=account2,
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            partner_organisation=organisation2,
        )
        AccountBenefit.objects.create(
            account=account1,
            partnership=partnership1,
            benefit=benefit,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            allocation=1,
        )
        AccountBenefit.objects.create(
            account=account2,
            partnership=partnership2,
            benefit=benefit,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            allocation=2,
        )
        queryset = Partnership.objects.credits_usage_annotation()

        # Act
        qs1 = filter_partnership_credits(queryset, "", selection="under_limit")
        qs2 = filter_partnership_credits(queryset, "", selection="over_limit")
        qs3 = filter_partnership_credits(queryset, "", selection="")

        # Assert
        self.assertQuerySetEqual(qs1, [partnership1])
        self.assertQuerySetEqual(qs2, [partnership2])
        self.assertQuerySetEqual(qs3, {partnership1, partnership2}, ordered=False)
