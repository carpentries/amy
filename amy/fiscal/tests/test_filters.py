from datetime import date

from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce
from django.test import TestCase

from fiscal.models import Membership
from fiscal.filters import MembershipFilter, MembershipTrainingsFilter
from workshops.models import Organization, Member, MemberRole, Role, Person, Task, Event


class TestMembershipFilter(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = Membership
        member_role = MemberRole.objects.first()

        # create a test membership that should be selected in filters
        cls.organization = Organization.objects.create(
            fullname="Test Organization", domain="example.org"
        )
        cls.membership = Membership.objects.create(
            name="Test Membership",
            variant="Bronze",
            agreement_start=date.today(),
            agreement_end=date.today(),
            contribution_type="Financial",
            public_instructor_training_seats=1,
        )
        cls.member = Member.objects.create(
            membership=cls.membership, organization=cls.organization, role=member_role
        )
        # create a test membership that sphould be filtered out
        cls.organization2 = Organization.objects.create(
            fullname="To Be Filtered Out", domain="example2.org"
        )
        cls.membership2 = Membership.objects.create(
            name="To Be Filtered Out",
            variant="Silver",
            agreement_start=date(2015, 1, 1),
            agreement_end=date(2016, 1, 1),
            contribution_type="Person-days",
            public_instructor_training_seats=0,
        )
        cls.member2 = Member.objects.create(
            membership=cls.membership2, organization=cls.organization2, role=member_role
        )
        cls.qs = Membership.objects.all().annotate(
            instructor_training_seats_total=(
                # Public
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # Coalesce returns first non-NULL value
                + Coalesce("public_instructor_training_seats_rolled_from_previous", 0)
                # Inhouse
                + F("inhouse_instructor_training_seats")
                + F("additional_inhouse_instructor_training_seats")
                + Coalesce("inhouse_instructor_training_seats_rolled_from_previous", 0)
            ),
            instructor_training_seats_remaining=(
                # Public
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # Coalesce returns first non-NULL value
                + Coalesce("public_instructor_training_seats_rolled_from_previous", 0)
                - Count(
                    "task", filter=Q(task__role__name="learner", task__seat_public=True)
                )
                - Coalesce("public_instructor_training_seats_rolled_over", 0)
                # Inhouse
                + F("inhouse_instructor_training_seats")
                + F("additional_inhouse_instructor_training_seats")
                + Coalesce("inhouse_instructor_training_seats_rolled_from_previous", 0)
                - Count(
                    "task",
                    filter=Q(task__role__name="learner", task__seat_public=False),
                )
                - Coalesce("inhouse_instructor_training_seats_rolled_over", 0)
            ),
        )

        # create 2 used seats on test membership
        # will make remaining seats negative
        cls.event = Event.objects.create(
            host=cls.organization,
            sponsor=cls.organization,
            membership=cls.membership,
            slug="2023-02-16-ttt-test",
        )
        cls.person = Person.objects.create(personal="Test", username="test")
        cls.person2 = Person.objects.create(personal="Test2", username="test2")
        cls.role = Role.objects.create(name="learner", verbose_name="Learner")
        cls.task = Task.objects.create(
            event=cls.event,
            person=cls.person,
            role=cls.role,
            seat_membership=cls.membership,
            seat_public=True,
        )
        cls.task2 = Task.objects.create(
            event=cls.event,
            person=cls.person2,
            role=cls.role,
            seat_membership=cls.membership,
            seat_public=True,
        )

        # get filterset
        cls.filterset = MembershipFilter({})

    @classmethod
    def tearDownClass(cls) -> None:
        # clean up used seats
        cls.task.delete()
        cls.task2.delete()
        cls.event.delete()
        cls.person.delete()
        cls.person2.delete()
        cls.role.delete()

        # clean up memberships
        cls.member.delete()
        cls.membership.delete()
        cls.organization.delete()
        cls.member2.delete()
        cls.membership2.delete()
        cls.organization2.delete()

    def test_fields(self):
        # Arrange & Act stages happen in setUpClass()
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
                "nonpositive_remaining_seats_only",
                "order_by",
            },
        )

    def test_filter_active_only(self):
        # Arrange
        name = "active_only"
        value = True

        # Act
        result = self.filterset.filters[name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_organization_name(self):
        # Arrange
        filter_name = "organization_name"
        value = "Test Organization"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.membership])

    def test_filter_variant(self):
        # Arrange
        filter_name = "variant"
        value = "Bronze"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_contribution_type(self):
        # Arrange
        filter_name = "contribution_type"
        value = "Financial"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_training_seats_only(self):
        # Arrange
        filter_name = "training_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_nonpositive_remaining_seats_only(self):
        # Arrange
        filter_name = "nonpositive_remaining_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_order_by(self):
        # Arrange
        filter_name = "order_by"
        results = {}
        expected_results = {
            "agreement_start": [self.membership2, self.membership],
            "agreement_end": [self.membership2, self.membership],
            "instructor_training_seats_remaining": [self.membership, self.membership2],
        }

        # Act
        for value in expected_results.keys():
            results[value] = self.filterset.filters[filter_name].filter(
                self.qs, [value]
            )

        # Assert
        for value in results.keys():
            self.assertQuerysetEqual(results[value], expected_results[value])


class TestMembershipTrainingsFilter(TestCase):
    """
    Duplicate of TestMembershipFilter with some fields removed.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = Membership
        member_role = MemberRole.objects.first()

        # create a test membership that should be selected in filters
        cls.organization = Organization.objects.create(
            fullname="Test Organization", domain="example.org"
        )
        cls.membership = Membership.objects.create(
            name="Test Membership",
            variant="Bronze",
            agreement_start=date.today(),
            agreement_end=date.today(),
            contribution_type="Financial",
            public_instructor_training_seats=1,
        )
        cls.member = Member.objects.create(
            membership=cls.membership, organization=cls.organization, role=member_role
        )
        # create a test membership that sphould be filtered out
        cls.organization2 = Organization.objects.create(
            fullname="To Be Filtered Out", domain="example2.org"
        )
        cls.membership2 = Membership.objects.create(
            name="To Be Filtered Out",
            variant="Silver",
            agreement_start=date(2015, 1, 1),
            agreement_end=date(2016, 1, 1),
            contribution_type="Person-days",
            public_instructor_training_seats=0,
        )
        cls.member2 = Member.objects.create(
            membership=cls.membership2, organization=cls.organization2, role=member_role
        )
        cls.qs = Membership.objects.all().annotate(
            instructor_training_seats_total=(
                # Public
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # Coalesce returns first non-NULL value
                + Coalesce("public_instructor_training_seats_rolled_from_previous", 0)
                # Inhouse
                + F("inhouse_instructor_training_seats")
                + F("additional_inhouse_instructor_training_seats")
                + Coalesce("inhouse_instructor_training_seats_rolled_from_previous", 0)
            ),
            instructor_training_seats_utilized=(
                Count("task", filter=Q(task__role__name="learner"))
            ),
            instructor_training_seats_remaining=(
                # Public
                F("public_instructor_training_seats")
                + F("additional_public_instructor_training_seats")
                # Coalesce returns first non-NULL value
                + Coalesce("public_instructor_training_seats_rolled_from_previous", 0)
                - Count(
                    "task", filter=Q(task__role__name="learner", task__seat_public=True)
                )
                - Coalesce("public_instructor_training_seats_rolled_over", 0)
                # Inhouse
                + F("inhouse_instructor_training_seats")
                + F("additional_inhouse_instructor_training_seats")
                + Coalesce("inhouse_instructor_training_seats_rolled_from_previous", 0)
                - Count(
                    "task",
                    filter=Q(task__role__name="learner", task__seat_public=False),
                )
                - Coalesce("inhouse_instructor_training_seats_rolled_over", 0)
            ),
        )

        # create 2 used seats on test membership
        # will make remaining seats negative
        cls.event = Event.objects.create(
            host=cls.organization,
            sponsor=cls.organization,
            membership=cls.membership,
            slug="2023-02-16-ttt-test",
        )
        cls.person = Person.objects.create(personal="Test", username="test")
        cls.person2 = Person.objects.create(personal="Test2", username="test2")
        cls.role = Role.objects.create(name="learner", verbose_name="Learner")
        cls.task = Task.objects.create(
            event=cls.event,
            person=cls.person,
            role=cls.role,
            seat_membership=cls.membership,
            seat_public=True,
        )
        cls.task2 = Task.objects.create(
            event=cls.event,
            person=cls.person2,
            role=cls.role,
            seat_membership=cls.membership,
            seat_public=True,
        )

        cls.filterset = MembershipTrainingsFilter({})

    @classmethod
    def tearDownClass(cls) -> None:
        # clean up used seats
        cls.task.delete()
        cls.task2.delete()
        cls.event.delete()
        cls.person.delete()
        cls.person2.delete()
        cls.role.delete()

        # clean up memberships
        cls.member.delete()
        cls.membership.delete()
        cls.organization.delete()
        cls.member2.delete()
        cls.membership2.delete()
        cls.organization2.delete()

    def test_fields(self):
        # Arrange & Act stages happen in setUpClass()
        # Assert
        self.assertEqual(
            set(self.filterset.filters.keys()),
            {
                "organization_name",
                "active_only",
                "training_seats_only",
                "nonpositive_remaining_seats_only",
                "order_by",
            },
        )

    def test_filter_active_only(self):
        # Arrange
        name = "active_only"
        value = True

        # Act
        result = self.filterset.filters[name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_organization_name(self):
        # Arrange
        filter_name = "organization_name"
        value = "Test Organization"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.membership])

    def test_filter_training_seats_only(self):
        # Arrange
        filter_name = "training_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_nonpositive_remaining_seats_only(self):
        # Arrange
        filter_name = "nonpositive_remaining_seats_only"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertTrue(self.membership in result)
        self.assertFalse(self.membership2 in result)

    def test_filter_order_by(self):
        # Arrange
        filter_name = "order_by"
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
        for value in expected_results.keys():
            results[value] = self.filterset.filters[filter_name].filter(
                self.qs, [value]
            )

        # Assert
        for value in results.keys():
            self.assertQuerysetEqual(results[value], expected_results[value])
