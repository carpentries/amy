from datetime import date, timedelta
from typing import List

from django.urls import reverse
import django_comments

from fiscal.forms import (
    MembershipCreateForm,
    MembershipExtensionForm,
    MembershipForm,
    MembershipRollOverForm,
)
from fiscal.models import MembershipPersonRole, MembershipTask
from workshops.models import (
    Event,
    Member,
    MemberRole,
    Membership,
    Organization,
    Role,
    Tag,
    Task,
)
from workshops.tests.base import TestBase

CommentModel = django_comments.get_model()


class TestMembership(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpTags()

        self.learner = Role.objects.get(name="learner")
        self.instructor = Role.objects.get(name="instructor")
        self.TTT = Tag.objects.get(name="TTT")
        self.cancelled = Tag.objects.get(name="cancelled")

        # parametrize membership creation
        self.agreement_start = date.today() - timedelta(days=180)
        self.agreement_start_next_day = self.agreement_start + timedelta(days=1)
        self.agreement_end = date.today() + timedelta(days=180)
        self.workshop_interval = timedelta(days=30)

        self.dc = Organization.objects.create(
            domain="datacarpentry.org",
            fullname="Data Carpentry",
        )

        # let's add a membership for one of the organizations
        self.current = Membership.objects.create(
            variant="partner",
            agreement_start=self.agreement_start,
            agreement_end=self.agreement_end,
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
            inhouse_instructor_training_seats=14,
            additional_inhouse_instructor_training_seats=5,
        )
        Member.objects.create(
            membership=self.current,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )

    def setUpTasks(self):
        # create a couple of workshops that span outside of agreement duration
        self_organized_admin = Organization.objects.get(domain="self-organized")
        data = [
            [self.agreement_start - timedelta(days=180), self_organized_admin],
            [self.agreement_start - timedelta(days=1), self.dc],
            [self.agreement_start - timedelta(days=1), self_organized_admin],
            [self.agreement_end + timedelta(days=1), self.dc],
        ]
        events = [
            Event(
                slug="event-outside-agreement-range-{}".format(i),
                host=self.org_beta,
                sponsor=self.org_beta,
                membership=self.current,
                # create each event starts roughly month later
                start=start_date,
                end=start_date + timedelta(days=1),
                administrator=admin,
            )
            for i, (start_date, admin) in enumerate(data)
        ]
        Event.objects.bulk_create(events)

        self_org_events = [
            Event(
                slug="event-self-org-{}".format(i),
                host=self.org_beta,
                sponsor=self.org_beta,
                membership=self.current,
                # create each event starts roughly month later
                start=self.agreement_start + i * self.workshop_interval,
                end=self.agreement_start_next_day + i * self.workshop_interval,
                administrator=self_organized_admin,
            )
            for i in range(10)
        ]
        no_fee_events = [
            Event(
                slug="event-no-fee-{}".format(i),
                host=self.org_beta,
                sponsor=self.org_beta,
                membership=self.current,
                # create each event starts roughly month later
                start=self.agreement_start + i * self.workshop_interval,
                end=self.agreement_start_next_day + i * self.workshop_interval,
                # just to satisfy the criteria
                administrator=self.dc,
            )
            for i in range(10)
        ]
        cancelled_events = [
            Event(
                slug="event-cancelled-{}".format(i),
                host=self.org_beta,
                sponsor=self.org_beta,
                membership=self.current,
                # create each event starts roughly month later
                start=self.agreement_start + i * self.workshop_interval,
                end=self.agreement_start_next_day + i * self.workshop_interval,
                # just to satisfy the criteria
                administrator=self.dc,
            )
            for i in range(10)
        ]
        self_org_events = Event.objects.bulk_create(self_org_events)
        no_fee_events = Event.objects.bulk_create(no_fee_events)
        cancelled_events = Event.objects.bulk_create(cancelled_events)
        self.TTT.event_set.set(self_org_events + no_fee_events)
        self.cancelled.event_set.set(cancelled_events)

        tasks = [
            Task(
                event=e,
                person=self.admin,
                role=self.learner,
                seat_membership=self.current,
            )
            for e in self_org_events[:5]
        ]
        Task.objects.bulk_create(tasks)

    def test_multiple_memberships(self):
        """Ensure we can have multiple memberships (even overlapping)."""
        overlapping = Membership.objects.create(
            variant="partner",
            agreement_start=date(2015, 7, 1),
            agreement_end=date(2016, 6, 30),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
        )
        Member.objects.create(
            membership=overlapping,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )

        self.assertIn(self.current, self.org_beta.memberships.all())
        self.assertIn(overlapping, self.org_beta.memberships.all())

    def test_workshops_without_admin_fee(self):
        """Ensure we calculate properly number of workshops per year."""
        self.setUpTasks()
        self.assertEqual(self.current.workshops_without_admin_fee_per_agreement, 10)
        self.assertEqual(self.current.workshops_without_admin_fee_total_allowed, 10)
        self.assertEqual(self.current.workshops_without_admin_fee_completed, 7)
        self.assertEqual(self.current.workshops_without_admin_fee_planned, 3)
        self.assertEqual(self.current.workshops_without_admin_fee_remaining, 0)

    def test_delete_membership(self):
        """Test that we can delete membership instance"""
        response = self.client.post(reverse("membership_delete", args=[self.current.pk]))
        self.assertRedirects(response, reverse("all_memberships"))

        # self.assertEqual(self.org_beta.memberships.count(), 0)
        with self.assertRaises(Membership.DoesNotExist):
            self.current.refresh_from_db()

    def test_number_of_instructor_training_seats(self):
        """Ensure calculation of seats in the instructor training events is
        correct."""
        self.setUpTasks()
        self.assertEqual(self.current.public_instructor_training_seats, 25)
        self.assertEqual(self.current.additional_public_instructor_training_seats, 3)
        self.assertEqual(self.current.public_instructor_training_seats_total, 28)
        self.assertEqual(self.current.public_instructor_training_seats_utilized, 5)
        self.assertEqual(self.current.public_instructor_training_seats_remaining, 23)

    def test_active_on_date(self):
        self.assertFalse(self.current.active_on_date(self.agreement_start - timedelta(days=1)))
        self.assertTrue(self.current.active_on_date(self.agreement_start))
        self.assertTrue(self.current.active_on_date(self.agreement_end))
        self.assertFalse(self.current.active_on_date(self.agreement_end + timedelta(days=1)))

    def test_active_on_date_with_grace_before(self):
        self.assertFalse(
            self.current.active_on_date(
                self.agreement_start - timedelta(days=91),
                grace_before=90,
                grace_after=60,
            )
        )
        self.assertTrue(
            self.current.active_on_date(
                self.agreement_start - timedelta(days=90),
                grace_before=90,
                grace_after=60,
            )
        )

    def test_active_on_date_with_grace_after(self):
        self.assertTrue(
            self.current.active_on_date(self.agreement_end + timedelta(days=60), grace_before=90, grace_after=60)
        )
        self.assertFalse(
            self.current.active_on_date(self.agreement_end + timedelta(days=61), grace_before=90, grace_after=60)
        )


class TestMembershipConsortiumCountingBase(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpTags()

        self.learner = Role.objects.get(name="learner")
        self.instructor = Role.objects.get(name="instructor")
        self.TTT = Tag.objects.get(name="TTT")
        self.cancelled = Tag.objects.get(name="cancelled")

        self.self_organized = Organization.objects.get(domain="self-organized")
        self.dc = Organization.objects.create(
            domain="datacarpentry.org",
            fullname="Data Carpentry",
        )

        self.setUpMembership()

    def setUpMembership(self):
        self.agreement_start = date.today() - timedelta(days=180)
        self.agreement_end = date.today() + timedelta(days=180)
        self.membership = Membership.objects.create(
            name="Greek Consortium",
            variant="partner",
            agreement_start=self.agreement_start,
            agreement_end=self.agreement_end,
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            workshops_without_admin_fee_rolled_from_previous=2,
            workshops_without_admin_fee_rolled_over=5,
            public_instructor_training_seats=6,
            additional_public_instructor_training_seats=4,
            public_instructor_training_seats_rolled_from_previous=2,
            public_instructor_training_seats_rolled_over=5,
            inhouse_instructor_training_seats=2,
            additional_inhouse_instructor_training_seats=5,
            inhouse_instructor_training_seats_rolled_from_previous=3,
            inhouse_instructor_training_seats_rolled_over=3,
        )
        Member.objects.bulk_create(
            [
                Member(
                    membership=self.membership,
                    organization=self.org_alpha,
                    role=MemberRole.objects.first(),
                ),
                Member(
                    membership=self.membership,
                    organization=self.org_beta,
                    role=MemberRole.objects.last(),
                ),
            ]
        )

    def setUpWorkshops(
        self,
        *categories,
        count: int = 1,
        administrator: Organization = None,
    ) -> List[Event]:
        if not categories:
            return []

        events: List[Event] = []
        if not administrator:
            administrator = self.dc

        if "cancelled" in categories:
            cancelled_events = [
                Event(
                    slug=f"event-cancelled-{i}",
                    host=self.org_alpha,
                    sponsor=self.org_alpha,
                    membership=self.membership,
                    start=self.agreement_start,
                    end=self.agreement_start + timedelta(days=1),
                    administrator=administrator,
                )
                for i in range(count)
            ]
            cancelled_events = Event.objects.bulk_create(cancelled_events)
            self.cancelled.event_set.set(cancelled_events)
            events += cancelled_events

        if "self-organised" in categories:
            self_organised = [
                Event(
                    slug=f"event-self-organised-{i}",
                    host=self.org_alpha,
                    sponsor=self.org_alpha,
                    membership=self.membership,
                    start=self.agreement_start,
                    end=self.agreement_start + timedelta(days=1),
                    administrator=self.self_organized,
                )
                for i in range(count)
            ]
            self_organised = Event.objects.bulk_create(self_organised)
            events += self_organised

        if "completed" in categories:
            completed_events = [
                Event(
                    slug=f"event-completed-{i}",
                    host=self.org_alpha,
                    sponsor=self.org_alpha,
                    membership=self.membership,
                    start=self.agreement_start,
                    end=self.agreement_start + timedelta(days=1),
                    administrator=administrator,
                )
                for i in range(count)
            ]
            completed_events = Event.objects.bulk_create(completed_events)
            events += completed_events

        if "planned" in categories:
            planned_events = [
                Event(
                    slug=f"event-planned-{i}",
                    host=self.org_alpha,
                    sponsor=self.org_alpha,
                    membership=self.membership,
                    start=date.today() + timedelta(days=1),
                    end=date.today() + timedelta(days=2),
                    administrator=administrator,
                )
                for i in range(count)
            ]
            planned_events = Event.objects.bulk_create(planned_events)
            events += planned_events

        return events

    def setUpTasks(self, count: int, public: bool = True) -> List[Task]:
        tasks = self.membership.task_set.bulk_create(
            [
                Task(
                    role=self.learner,
                    person=self.admin,
                    event=Event.objects.create(
                        slug=f"event-learner-{i}",
                        host=self.dc,
                        sponsor=self.dc,
                        membership=self.membership,
                        administrator=self.org_alpha,
                    ),
                    seat_membership=self.membership,
                    seat_public=public,
                )
                for i in range(count)
            ]
        )
        return tasks


class TestMembershipConsortiumCountingCentrallyOrganisedWorkshops(TestMembershipConsortiumCountingBase):
    def test_queryset(self):
        events = self.setUpWorkshops("completed", "planned", count=1)
        self.assertTrue(Event.objects.all())
        self.assertEqual(set(self.membership._workshops_without_admin_fee_queryset()), set(events))

    def test_queryset_completed(self):
        events = self.setUpWorkshops("completed", count=1)
        self.setUpWorkshops("planned", count=1)
        self.assertTrue(Event.objects.all())
        self.assertEqual(
            set(self.membership._workshops_without_admin_fee_completed_queryset()),
            set(events),
        )

    def test_queryset_planned(self):
        self.setUpWorkshops("completed", count=1)
        events = self.setUpWorkshops("planned", count=1)
        self.assertTrue(Event.objects.all())
        self.assertEqual(
            set(self.membership._workshops_without_admin_fee_planned_queryset()),
            set(events),
        )

    def test_cancelled_workshops_are_not_counted(self):
        self.setUpWorkshops("cancelled", count=2)
        self.assertTrue(Event.objects.all())
        self.assertEqual(list(self.membership._workshops_without_admin_fee_queryset()), [])

    def test_self_organised_workshops_are_not_counted(self):
        self.setUpWorkshops("self-organised", count=2)
        self.assertTrue(Event.objects.all())
        self.assertEqual(list(self.membership._workshops_without_admin_fee_queryset()), [])

    def test_total_allowed_workshops_count(self):
        # agreement: 10, rolled from previous: 2
        # 10 + 2 = 12
        self.assertEqual(self.membership.workshops_without_admin_fee_total_allowed, 12)

    def test_available_workshops_count(self):
        # agreement: 10, rolled from previous: 2, rolled over: 5
        # 10 + 2 - 5 = 7
        self.assertEqual(self.membership.workshops_without_admin_fee_available, 7)

    def test_completed_workshops_count(self):
        self.setUpWorkshops("completed", count=3)
        self.assertTrue(Event.objects.all())
        self.assertEqual(self.membership.workshops_without_admin_fee_completed, 3)
        self.assertEqual(self.membership.workshops_discounted_completed, 0)
        self.assertEqual(self.membership.workshops_without_admin_fee_remaining, 4)

    def test_completed_workshops_count_maxed_out(self):
        self.setUpWorkshops("completed", count=10)
        self.assertTrue(Event.objects.all())
        self.assertEqual(self.membership.workshops_without_admin_fee_completed, 7)
        self.assertEqual(self.membership.workshops_discounted_completed, 3)
        self.assertEqual(self.membership.workshops_without_admin_fee_remaining, 0)

    def test_planned_workshops_count(self):
        self.setUpWorkshops("planned", count=4)
        self.assertTrue(Event.objects.all())
        self.assertEqual(self.membership.workshops_without_admin_fee_planned, 4)
        self.assertEqual(self.membership.workshops_discounted_planned, 0)
        self.assertEqual(self.membership.workshops_without_admin_fee_remaining, 3)

    def test_planned_workshops_count_maxed_out(self):
        self.setUpWorkshops("planned", count=10)
        self.assertTrue(Event.objects.all())
        self.assertEqual(self.membership.workshops_without_admin_fee_planned, 7)
        self.assertEqual(self.membership.workshops_discounted_planned, 3)
        self.assertEqual(self.membership.workshops_without_admin_fee_remaining, 0)

    def test_remaining_workshops_count(self):
        self.setUpWorkshops("cancelled", "self-organised", "completed", "planned", count=2)
        self.assertTrue(Event.objects.all())
        # number of available: 10 + 2 - 5 = 7
        # number of workshops counted: 2 * completed + 2 * planned
        self.assertEqual(self.membership.workshops_without_admin_fee_remaining, 3)
        self.assertEqual(self.membership.workshops_discounted_completed, 0)
        self.assertEqual(self.membership.workshops_discounted_planned, 0)


class TestMembershipConsortiumCountingSelfOrganisedWorkshops(TestMembershipConsortiumCountingBase):
    def test_cancelled_workshops_are_not_counted(self):
        self.setUpWorkshops("cancelled", count=2, administrator=self.self_organized)
        self.assertTrue(Event.objects.all())
        self.assertEqual(list(self.membership._self_organized_workshops_queryset()), [])

    def test_centrally_organised_workshops_are_not_counted(self):
        self.setUpWorkshops("completed", count=2, administrator=self.dc)
        self.assertTrue(Event.objects.all())
        self.assertEqual(list(self.membership._self_organized_workshops_queryset()), [])

    def test_completed_workshops(self):
        self.setUpWorkshops("completed", count=3, administrator=self.self_organized)
        self.assertTrue(Event.objects.all())
        self.assertEqual(self.membership.self_organized_workshops_completed, 3)

    def test_planned_workshops(self):
        self.setUpWorkshops("planned", count=4, administrator=self.self_organized)
        self.assertTrue(Event.objects.all())
        self.assertEqual(self.membership.self_organized_workshops_planned, 4)


class TestMembershipConsortiumCountingPublicInstructorTrainingSeats(TestMembershipConsortiumCountingBase):
    def test_seats_total(self):
        # rolled from previous are counted into the total
        self.assertEqual(self.membership.public_instructor_training_seats_total, 12)

    def test_seats_utilized(self):
        self.setUpTasks(count=5)
        self.assertEqual(self.membership.public_instructor_training_seats_utilized, 5)

    def test_seats_remaining(self):
        self.setUpTasks(count=5)
        # total and rolled over from previous: 10 + 2
        # utilized: 5
        # rolled-over: 5
        # remaining: 2
        self.assertEqual(self.membership.public_instructor_training_seats_remaining, 2)


class TestMembershipConsortiumCountingInhouseInstructorTrainingSeats(TestMembershipConsortiumCountingBase):
    def test_seats_total(self):
        # seats: 2
        # additional: 5
        # rolled from previous: 3
        # total: 10
        self.assertEqual(self.membership.inhouse_instructor_training_seats_total, 10)

    def test_seats_utilized(self):
        self.setUpTasks(count=5, public=False)
        self.assertEqual(self.membership.inhouse_instructor_training_seats_utilized, 5)

    def test_seats_remaining(self):
        self.setUpTasks(count=5, public=False)
        # total and rolled over from previous: 10
        # utilized: 5
        # rolled-over: 3
        # remaining: 2
        self.assertEqual(self.membership.inhouse_instructor_training_seats_remaining, 2)


class TestMembershipForms(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpTags()

    def test_creating_membership_with_no_comment(self):
        """Ensure that no comment is added when MembershipCreateForm without
        comment content is saved."""
        self.assertEqual(CommentModel.objects.count(), 0)
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 28),
            "agreement_end": date(2022, 1, 28),
            "agreement_link": "https://example.com",
            "variant": "partner",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
            "comment": "",
        }
        form = MembershipCreateForm(data)
        form.save()
        self.assertEqual(CommentModel.objects.count(), 0)

    def test_creating_membership_with_comment(self):
        """Ensure that a comment is added when MembershipCreateForm with
        comment content is saved."""
        self.assertEqual(CommentModel.objects.count(), 0)
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 28),
            "agreement_end": date(2022, 1, 28),
            "agreement_link": "https://example.com",
            "variant": "partner",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
            "comment": "This is a test comment.",
        }
        form = MembershipCreateForm(data)
        obj = form.save()
        self.assertEqual(CommentModel.objects.count(), 1)
        comment = CommentModel.objects.first()
        self.assertEqual(comment.comment, "This is a test comment.")
        self.assertIn(comment, CommentModel.objects.for_model(obj))

    def test_membership_edit_form_no_comment(self):
        """Ensure membership edit form works and doesn't provide `comment` field.

        This is a regression test against #1437:
        https://github.com/swcarpentry/amy/issues/1437
        """
        # parametrize membership creation
        agreement_start = date.today() - timedelta(days=180)
        agreement_end = date.today() + timedelta(days=180)

        # let's add a membership for one of the organizations
        membership = Membership.objects.create(
            name="Test Membership",
            consortium=False,
            variant="partner",
            agreement_start=agreement_start,
            agreement_end=agreement_end,
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )

        self.assertNotIn("comment", MembershipForm.Meta.fields)

        self.assertEqual(CommentModel.objects.count(), 0)
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 28),
            "agreement_end": date(2022, 1, 28),
            "agreement_link": "https://example.com",
            "variant": "partner",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
        }
        form = MembershipForm(data, instance=membership)
        form.save()
        self.assertEqual(CommentModel.objects.count(), 0)

    def test_membership_agreement_dates_validation(self):
        """Validate invalid agreement end date (can't be sooner than start date)."""
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 26),
            "agreement_end": date(2020, 1, 26),
            "agreement_link": "https://example.com",
            "variant": "partner",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
        }
        form = MembershipForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["agreement_end"],
            ["Agreement end date can't be sooner than the start date."],
        )

    def test_changing_consortium_to_nonconsortium(self):
        membership = Membership.objects.create(
            name="Test Membership",
            consortium=True,
            variant="partner",
            agreement_start=date(2021, 3, 21),
            agreement_end=date(2022, 3, 21),
            agreement_link="https://example.com",
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )
        m1 = Member.objects.create(
            membership=membership,
            organization=self.org_alpha,
            role=MemberRole.objects.first(),
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.last(),
        )

        data = {
            "name": membership.name,
            "consortium": False,  # changing to non-consortium
            "public_status": membership.public_status,
            "agreement_start": membership.agreement_start,
            "agreement_end": membership.agreement_end,
            "agreement_link": membership.agreement_link,
            "variant": membership.variant,
            "contribution_type": membership.contribution_type,
            "public_instructor_training_seats": membership.public_instructor_training_seats,  # noqa
            "additional_public_instructor_training_seats": membership.additional_public_instructor_training_seats,  # noqa
            "inhouse_instructor_training_seats": membership.inhouse_instructor_training_seats,  # noqa
            "additional_inhouse_instructor_training_seats": membership.additional_inhouse_instructor_training_seats,  # noqa
        }
        form = MembershipForm(data, instance=membership)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["consortium"],
            [
                "Cannot change to non-consortium when there are multiple members "
                "assigned. Remove the members so that at most 1 is left."
            ],
        )

        # after deleting the member, form validates with no errors
        m1.delete()
        form = MembershipForm(data, instance=membership)
        self.assertTrue(form.is_valid())

    def test_edit_membership_rolled_fields(self):
        # Arrange
        membership1 = Membership.objects.create(
            name="Test Membership 1",
            consortium=False,
            variant="partner",
            agreement_start=date(2021, 8, 1),
            agreement_end=date(2022, 7, 31),
            contribution_type="financial",
            agreement_link="https://example.com",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=10,
            inhouse_instructor_training_seats=10,
        )
        membership2 = Membership.objects.create(
            name="Test Membership 2",
            consortium=False,
            variant="partner",
            agreement_start=date(2022, 8, 1),
            agreement_end=date(2023, 7, 31),
            agreement_link="https://example.com",
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=10,
            inhouse_instructor_training_seats=10,
        )
        membership3 = Membership.objects.create(
            name="Test Membership 3",
            consortium=False,
            variant="partner",
            agreement_start=date(2023, 8, 1),
            agreement_end=date(2024, 7, 31),
            agreement_link="https://example.com",
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=10,
            inhouse_instructor_training_seats=10,
        )
        # 1st roll-over (only central workshops)
        membership1.rolled_to_membership = membership2
        membership1.workshops_without_admin_fee_rolled_over = 5
        membership2.workshops_without_admin_fee_rolled_from_previous = 5

        # 2nd roll-over (training seats of both kinds)
        membership2.rolled_to_membership = membership3
        membership2.public_instructor_training_seats_rolled_over = 6
        membership2.inhouse_instructor_training_seats_rolled_over = 7
        membership3.public_instructor_training_seats_rolled_from_previous = 6
        membership3.inhouse_instructor_training_seats_rolled_from_previous = 7

        membership1.save()
        membership2.save()
        membership3.save()

        # Act
        data = {
            "name": membership2.name,
            "public_status": membership2.public_status,
            "variant": membership2.variant,
            "agreement_start": membership2.agreement_start,
            "agreement_end": membership2.agreement_end,
            "agreement_link": membership2.agreement_link,
            "contribution_type": membership2.contribution_type,
            "public_instructor_training_seats": membership2.public_instructor_training_seats,  # noqa
            "additional_public_instructor_training_seats": membership2.additional_public_instructor_training_seats,  # noqa
            "inhouse_instructor_training_seats": membership2.inhouse_instructor_training_seats,  # noqa
            "additional_inhouse_instructor_training_seats": membership2.additional_inhouse_instructor_training_seats,  # noqa
            "workshops_without_admin_fee_rolled_from_previous": 6,  # was 5
            "public_instructor_training_seats_rolled_over": 7,  # was 6
            "inhouse_instructor_training_seats_rolled_over": 8,  # was 7
        }
        self.client.post(reverse("membership_edit", args=[membership2.id]), data=data)
        membership1.refresh_from_db()
        membership2.refresh_from_db()
        membership3.refresh_from_db()

        # Assert
        self.assertEqual(
            membership1.workshops_without_admin_fee_rolled_over,
            6,
        )
        self.assertEqual(
            membership2.workshops_without_admin_fee_rolled_from_previous,
            6,
        )

        self.assertEqual(
            membership2.public_instructor_training_seats_rolled_over,
            7,
        )
        self.assertEqual(
            membership3.public_instructor_training_seats_rolled_from_previous,
            7,
        )

        self.assertEqual(
            membership2.inhouse_instructor_training_seats_rolled_over,
            8,
        )
        self.assertEqual(
            membership3.inhouse_instructor_training_seats_rolled_from_previous,
            8,
        )

    def test_membership_edit_extensions(self):
        for increment in (10, -5):  # +10 days, -5 days per extension
            with self.subTest(increment=increment):
                # Arrange
                agreement_end = date(2022, 7, 31)
                extensions = [10, 20, 30]
                membership = Membership.objects.create(
                    name="Test Membership 1",
                    consortium=False,
                    variant="partner",
                    agreement_start=date(2021, 8, 1),
                    agreement_end=agreement_end,
                    agreement_link="https://example.com",
                    extensions=extensions,
                    contribution_type="financial",
                    workshops_without_admin_fee_per_agreement=10,
                    public_instructor_training_seats=10,
                    inhouse_instructor_training_seats=10,
                )
                data = {
                    "name": membership.name,
                    "public_status": membership.public_status,
                    "variant": membership.variant,
                    "agreement_start": membership.agreement_start,
                    "agreement_end": membership.agreement_end,
                    "agreement_link": membership.agreement_link,
                    "extensions_0": extensions[0] + increment,
                    "extensions_1": extensions[1] + increment,
                    "extensions_2": extensions[2] + increment,
                    "contribution_type": membership.contribution_type,
                    "workshops_without_admin_fee_per_agreement": membership.workshops_without_admin_fee_per_agreement,  # noqa
                    "public_instructor_training_seats": membership.public_instructor_training_seats,  # noqa
                    "additional_public_instructor_training_seats": membership.additional_public_instructor_training_seats,  # noqa
                    "inhouse_instructor_training_seats": membership.inhouse_instructor_training_seats,  # noqa
                    "additional_inhouse_instructor_training_seats": membership.additional_inhouse_instructor_training_seats,  # noqa
                }
                str_ext = ", ".join(str(ext + increment) for ext in extensions)
                new_agreement_end = agreement_end + timedelta(days=3 * increment)
                msg = (
                    f"Extension days changed to following: {str_ext} days. New "
                    f"agreement end date: {new_agreement_end}."
                )

                # Act
                result = self.client.post(
                    reverse("membership_edit", args=[membership.id]),
                    data=data,
                    follow=False,
                )

                # Assert
                self.assertEqual(result.status_code, 302)  # form saved
                membership.refresh_from_db()
                self.assertEqual(
                    membership.extensions,
                    [extension + increment for extension in extensions],
                )
                self.assertEqual(membership.agreement_end, new_agreement_end)

                # check if comment was added
                comment = CommentModel.objects.for_model(membership).last()
                self.assertEqual(comment.comment, msg)


class TestNewMembershipWorkflow(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_new_nonconsortium_membership_redirects_to_details(self):
        """Ensure once created, new non-consortium membership redirects to it's details
        page."""
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "variant": "partner",
            "agreement_start": "2021-02-14",
            "agreement_end": "2022-02-14",
            "agreement_link": "https://example.com",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
        }
        response = self.client.post(reverse("membership_add"), data=data)
        latest_membership = Membership.objects.order_by("-id").first()

        self.assertRedirects(response, reverse("membership_details", args=[latest_membership.pk]))

    def test_new_consortium_membership_redirects_to_members(self):
        """Ensure once created, new consortium membership redirects to member page
        to edit the members."""
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": True,
            "public_status": "public",
            "variant": "partner",
            "agreement_start": "2021-02-14",
            "agreement_end": "2022-02-14",
            "agreement_link": "https://example.com",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
        }
        response = self.client.post(reverse("membership_add"), data=data)
        latest_membership = Membership.objects.order_by("-id").first()

        self.assertRedirects(response, reverse("membership_members", args=[latest_membership.pk]))

    def test_new_nonconsortium_membership_has_main_member(self):
        """Ensure once created, new non-consortium membership will have a default member
        organisation."""
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "variant": "partner",
            "agreement_start": "2021-02-14",
            "agreement_end": "2022-02-14",
            "agreement_link": "https://example.com",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
        }
        response = self.client.post(reverse("membership_add"), data=data, follow=True)

        latest_membership = Membership.objects.order_by("-id").first()
        self.assertEqual(response.context["membership"], latest_membership)
        self.assertEqual(latest_membership.member_set.count(), 1)
        member = latest_membership.member_set.first()
        self.assertEqual(member.role.name, "main")
        self.assertEqual(member.organization, self.org_alpha)

    def test_new_consortium_membership_has_main_member(self):
        """Ensure once created, new consortium membership will have a default member
        organisation."""
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": True,
            "public_status": "public",
            "variant": "partner",
            "agreement_start": "2021-02-14",
            "agreement_end": "2022-02-14",
            "agreement_link": "https://example.com",
            "contribution_type": "financial",
            "public_instructor_training_seats": 0,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 0,
            "additional_inhouse_instructor_training_seats": 0,
        }
        response = self.client.post(reverse("membership_add"), data=data, follow=True)

        latest_membership = Membership.objects.order_by("-id").first()
        self.assertEqual(response.context["membership"], latest_membership)
        self.assertEqual(latest_membership.member_set.count(), 1)
        member = latest_membership.member_set.first()
        self.assertEqual(member.role.name, "contract_signatory")
        self.assertEqual(member.organization, self.org_alpha)


class TestMembershipExtension(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_form_simple_valid(self):
        data = {
            "agreement_start": "2021-02-27",
            "agreement_end": "2022-02-27",
            "new_agreement_end": "2022-02-28",
            "extension": "1",
        }

        form = MembershipExtensionForm(data)

        self.assertTrue(form.is_valid())

    def test_form_ignoring_fields(self):
        data = {
            # fields ignored
            "agreement_start": "invalid value",
            "agreement_end": "invalid value",
            "extension": "invalid value",
            # field accepted
            "new_agreement_end": "2021-08-10",
        }

        form = MembershipExtensionForm(data)

        self.assertTrue(form.is_valid())

    def test_form_validating_extension(self):
        data = [
            ("string", False),
            ("", False),
            ("2020-01-01", False),
            ("2021-01-01", False),
            ("2022-01-01", True),
        ]
        for end_date, valid in data:
            with self.subTest(date=end_date, valid=valid):
                form = MembershipExtensionForm(
                    dict(new_agreement_end=end_date),
                    initial=dict(agreement_end="2021-01-01"),
                )
                self.assertEqual(form.is_valid(), valid)

    def test_membership_extended(self):
        membership = Membership.objects.create(
            name="Test Membership",
            consortium=False,
            public_status="public",
            variant="partner",
            agreement_start="2020-03-01",
            agreement_end="2021-03-01",
            contribution_type="financial",
            public_instructor_training_seats=0,
            additional_public_instructor_training_seats=0,
        )
        Member.objects.create(
            organization=self.org_alpha,
            membership=membership,
            role=MemberRole.objects.first(),
        )
        data = {"new_agreement_end": date(2021, 3, 31)}

        response = self.client.post(
            reverse("membership_extend", args=[membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(response, reverse("membership_details", args=[membership.pk]))
        membership.refresh_from_db()
        self.assertEqual(membership.extensions, [30])
        self.assertEqual(membership.agreement_end, date(2021, 3, 31))

    def test_membership_extended_multiple_times(self):
        membership = Membership.objects.create(
            name="Test Membership",
            consortium=False,
            public_status="public",
            variant="partner",
            agreement_start="2020-03-01",
            agreement_end="2021-03-01",
            contribution_type="financial",
            public_instructor_training_seats=0,
            additional_public_instructor_training_seats=0,
        )
        Member.objects.create(
            organization=self.org_alpha,
            membership=membership,
            role=MemberRole.objects.first(),
        )
        data1 = {"new_agreement_end": date(2021, 3, 31)}
        data2 = {"new_agreement_end": date(2021, 5, 10)}
        data3 = {"new_agreement_end": date(2021, 6, 29)}

        self.client.post(reverse("membership_extend", args=[membership.pk]), data=data1)
        self.client.post(reverse("membership_extend", args=[membership.pk]), data=data2)
        self.client.post(reverse("membership_extend", args=[membership.pk]), data=data3)

        membership.refresh_from_db()
        self.assertEqual(membership.extensions, [30, 40, 50])
        self.assertEqual(membership.agreement_end, date(2021, 6, 29))

    def test_comment_added(self):
        # Arrange
        membership = Membership.objects.create(
            name="Test Membership",
            consortium=False,
            public_status="public",
            variant="partner",
            agreement_start="2020-03-01",
            agreement_end="2021-03-01",
            contribution_type="financial",
            public_instructor_training_seats=0,
            additional_public_instructor_training_seats=0,
        )
        Member.objects.create(
            organization=self.org_alpha,
            membership=membership,
            role=MemberRole.objects.first(),
        )
        comment = "Everything is awesome."
        data = {"new_agreement_end": date(2021, 3, 31), "comment": comment}
        today = date.today()
        expected_comment = (
            f"Extended membership by 30 days on {today} (new end date: 2021-03-31)." "\n\n----\n\n" f"{comment}"
        )

        # Act
        self.client.post(reverse("membership_extend", args=[membership.pk]), data=data)

        # Assert
        self.assertEqual(CommentModel.objects.for_model(membership).count(), 1)
        comment = CommentModel.objects.for_model(membership).first()
        self.assertEqual(comment.comment, expected_comment)


class TestMembershipCreateRollOver(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self.learner = Role.objects.get(name="learner")
        self._setUpUsersAndLogin()
        self.data = {
            "name": "Test Name",
            "consortium": True,
            "public_status": "public",
            "variant": "partner",
            "agreement_start": "2021-03-01",
            "agreement_end": "2022-03-01",
            "agreement_link": "https://example.com",
            "contribution_type": "financial",
            "workshops_without_admin_fee_per_agreement": 10,
            "public_instructor_training_seats": 12,
            "additional_public_instructor_training_seats": 0,
            "inhouse_instructor_training_seats": 9,
            "additional_inhouse_instructor_training_seats": 0,
        }
        self.dc = Organization.objects.create(
            domain="datacarpentry.org",
            fullname="Data Carpentry",
        )

    def setUpMembership(
        self,
        consortium: bool = False,
        workshops_without_admin_fee_per_agreement: int = 10,
        public_instructor_training_seats: int = 12,
        inhouse_instructor_training_seats: int = 9,
    ):
        self.membership = Membership.objects.create(
            name="Test Membership",
            consortium=consortium,
            public_status="public",
            variant="partner",
            agreement_start=date(2020, 3, 1),
            agreement_end=date(2021, 3, 1),
            agreement_link="https://example.com",
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=workshops_without_admin_fee_per_agreement,  # noqa
            public_instructor_training_seats=public_instructor_training_seats,  # noqa
            additional_public_instructor_training_seats=0,
            inhouse_instructor_training_seats=inhouse_instructor_training_seats,  # noqa
            additional_inhouse_instructor_training_seats=0,
        )
        Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=MemberRole.objects.first(),
        )
        MembershipTask.objects.create(
            person=self.hermione,
            membership=self.membership,
            role=MembershipPersonRole.objects.first(),
        )

    def test_form_simple_valid(self):
        form = MembershipRollOverForm(self.data)
        self.assertTrue(form.is_valid())

    def test_form_validation_rolled_fields(self):
        test_data = [
            # PASS: centrally org. workshops maxed out, others set to 0
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                    "public_instructor_training_seats_rolled_from_previous": 0,
                    "inhouse_instructor_training_seats_rolled_from_previous": 0,
                },
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                },
                True,
                [],
            ),
            # FAIL: more (1) centrally org. workshops than allowed (0)
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                    "public_instructor_training_seats_rolled_from_previous": 0,
                    "inhouse_instructor_training_seats_rolled_from_previous": 0,
                },
                {
                    "workshops_without_admin_fee_rolled_from_previous": 0,
                },
                False,
                ["workshops_without_admin_fee_rolled_from_previous"],
            ),
            # PASS: public ITT seats maxed out, others set to 0
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 0,
                    "public_instructor_training_seats_rolled_from_previous": 1,
                    "inhouse_instructor_training_seats_rolled_from_previous": 0,
                },
                {
                    "public_instructor_training_seats_rolled_from_previous": 1,
                },
                True,
                [],
            ),
            # FAIL: more (1) public ITT seats than allowed (0)
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 0,
                    "public_instructor_training_seats_rolled_from_previous": 1,
                    "inhouse_instructor_training_seats_rolled_from_previous": 0,
                },
                {
                    "public_instructor_training_seats_rolled_from_previous": 0,
                },
                False,
                ["public_instructor_training_seats_rolled_from_previous"],
            ),
            # PASS: in-house ITT seats maxed out, others set to 0
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 0,
                    "public_instructor_training_seats_rolled_from_previous": 0,
                    "inhouse_instructor_training_seats_rolled_from_previous": 1,
                },
                {
                    "inhouse_instructor_training_seats_rolled_from_previous": 1,
                },
                True,
                [],
            ),
            # FAIL: more (1) in-house ITT seats than allowed (0)
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 0,
                    "public_instructor_training_seats_rolled_from_previous": 0,
                    "inhouse_instructor_training_seats_rolled_from_previous": 1,
                },
                {
                    "inhouse_instructor_training_seats_rolled_from_previous": 0,
                },
                False,
                ["inhouse_instructor_training_seats_rolled_from_previous"],
            ),
            # FAIL: no max_values provided, so all fields default to 0
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                    "public_instructor_training_seats_rolled_from_previous": 1,
                    "inhouse_instructor_training_seats_rolled_from_previous": 1,
                },
                {},
                False,
                [
                    "workshops_without_admin_fee_rolled_from_previous",
                    "public_instructor_training_seats_rolled_from_previous",
                    "inhouse_instructor_training_seats_rolled_from_previous",
                ],
            ),
            # PASS: all values within max_values ranges
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                    "public_instructor_training_seats_rolled_from_previous": 1,
                    "inhouse_instructor_training_seats_rolled_from_previous": 0,
                },
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                    "public_instructor_training_seats_rolled_from_previous": 2,
                    "inhouse_instructor_training_seats_rolled_from_previous": 0,
                },
                True,
                [],
            ),
            # FAIL: negative values
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": -1,
                    "public_instructor_training_seats_rolled_from_previous": -1,
                    "inhouse_instructor_training_seats_rolled_from_previous": -1,
                },
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                    "public_instructor_training_seats_rolled_from_previous": 1,
                    "inhouse_instructor_training_seats_rolled_from_previous": 1,
                },
                False,
                [
                    "workshops_without_admin_fee_rolled_from_previous",
                    "public_instructor_training_seats_rolled_from_previous",
                    "inhouse_instructor_training_seats_rolled_from_previous",
                ],
            ),
            # FAIL: too big values
            (
                {
                    "workshops_without_admin_fee_rolled_from_previous": 2,
                    "public_instructor_training_seats_rolled_from_previous": 2,
                    "inhouse_instructor_training_seats_rolled_from_previous": 2,
                },
                {
                    "workshops_without_admin_fee_rolled_from_previous": 1,
                    "public_instructor_training_seats_rolled_from_previous": 1,
                    "inhouse_instructor_training_seats_rolled_from_previous": 1,
                },
                False,
                [
                    "workshops_without_admin_fee_rolled_from_previous",
                    "public_instructor_training_seats_rolled_from_previous",
                    "inhouse_instructor_training_seats_rolled_from_previous",
                ],
            ),
        ]
        for data, max_values, is_valid, failed_fields in test_data:
            with self.subTest(max_values=max_values):
                data.update(self.data)
                form = MembershipRollOverForm(data, max_values=max_values)
                self.assertEqual(form.is_valid(), is_valid)
                if not is_valid:
                    self.assertEqual(set(failed_fields), form.errors.keys())

    def test_new_membership_nonconsortium_created(self):
        self.setUpMembership(consortium=False)

        response = self.client.post(
            reverse("membership_create_roll_over", args=[self.membership.pk]),
            data=self.data,
            follow=True,
        )

        last_membership = Membership.objects.order_by("pk").last()
        self.assertRedirects(response, reverse("membership_details", args=[last_membership.pk]))
        # main member should be copied over to the new membership when the
        # original membership is not a consortium
        self.assertEqual(last_membership.member_set.count(), 1)
        self.assertEqual(last_membership.member_set.first().organization, self.org_alpha)
        self.assertEqual(last_membership.member_set.first().role, MemberRole.objects.first())

    def test_new_membership_consortium_created(self):
        test_data = [True, False]

        for copy_members in test_data:
            # Membership needs to be created for each subtest.
            self.setUpMembership(consortium=True)

            with self.subTest(copy_members=copy_members):
                data = {
                    "copy_members": copy_members,
                    **self.data,
                }
                response = self.client.post(
                    reverse("membership_create_roll_over", args=[self.membership.pk]),
                    data=data,
                    follow=True,
                )

                last_membership = Membership.objects.order_by("pk").last()
                self.assertRedirects(response, reverse("membership_details", args=[last_membership.pk]))

                if copy_members:
                    self.assertEqual(last_membership.member_set.count(), 1)
                    self.assertEqual(last_membership.member_set.first().organization, self.org_alpha)
                    self.assertEqual(
                        last_membership.member_set.first().role,
                        MemberRole.objects.first(),
                    )
                else:
                    self.assertEqual(last_membership.member_set.count(), 0)

    def test_new_membership_persons_copied(self):
        test_data = [True, False]

        for copy_membership_tasks in test_data:
            # Membership needs to be created for each subtest.
            self.setUpMembership()

            with self.subTest(copy_membership_tasks=copy_membership_tasks):
                data = {
                    "copy_membership_tasks": copy_membership_tasks,
                    **self.data,
                }
                response = self.client.post(
                    reverse("membership_create_roll_over", args=[self.membership.pk]),
                    data=data,
                    follow=True,
                )

                last_membership = Membership.objects.order_by("pk").last()
                self.assertRedirects(response, reverse("membership_details", args=[last_membership.pk]))

                if copy_membership_tasks:
                    self.assertEqual(last_membership.membershiptask_set.count(), 1)
                    self.assertEqual(last_membership.membershiptask_set.first().person, self.hermione)
                    self.assertEqual(
                        last_membership.membershiptask_set.first().role,
                        MembershipPersonRole.objects.first(),
                    )
                else:
                    self.assertEqual(last_membership.membershiptask_set.count(), 0)

    def test_membership_rollovers(self):
        self.setUpMembership()
        data = {
            "name": "Test Membership",
            "workshops_without_admin_fee_rolled_from_previous": 3,
            "public_instructor_training_seats_rolled_from_previous": 2,
            "inhouse_instructor_training_seats_rolled_from_previous": 1,
            **self.data,
        }

        self.client.post(
            reverse("membership_create_roll_over", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        last_membership = Membership.objects.order_by("pk").last()
        self.membership.refresh_from_db()

        self.assertEqual(self.membership.workshops_without_admin_fee_per_agreement, 10)
        self.assertEqual(self.membership.public_instructor_training_seats, 12)
        self.assertEqual(self.membership.additional_public_instructor_training_seats, 0)
        self.assertEqual(self.membership.inhouse_instructor_training_seats, 9)
        self.assertEqual(self.membership.additional_inhouse_instructor_training_seats, 0)

        self.assertEqual(self.membership.workshops_without_admin_fee_rolled_from_previous, None)
        self.assertEqual(self.membership.public_instructor_training_seats_rolled_from_previous, None)
        self.assertEqual(self.membership.inhouse_instructor_training_seats_rolled_from_previous, None)

        self.assertEqual(self.membership.workshops_without_admin_fee_rolled_over, 3)
        self.assertEqual(self.membership.public_instructor_training_seats_rolled_over, 2)
        self.assertEqual(self.membership.inhouse_instructor_training_seats_rolled_over, 1)
        self.assertEqual(self.membership.rolled_to_membership, last_membership)

        # Special behavior of OneToOneField: will throw exception upon access if
        # the related object is not set. This means simple for `is None` won't work.
        with self.assertRaises(Membership.rolled_from_membership.RelatedObjectDoesNotExist):
            self.membership.rolled_from_membership

        self.assertEqual(last_membership.workshops_without_admin_fee_per_agreement, 10)
        self.assertEqual(last_membership.public_instructor_training_seats, 12)
        self.assertEqual(last_membership.additional_public_instructor_training_seats, 0)
        self.assertEqual(last_membership.inhouse_instructor_training_seats, 9)
        self.assertEqual(last_membership.additional_inhouse_instructor_training_seats, 0)
        self.assertEqual(last_membership.workshops_without_admin_fee_rolled_from_previous, 3)
        self.assertEqual(last_membership.public_instructor_training_seats_rolled_from_previous, 2)
        self.assertEqual(last_membership.inhouse_instructor_training_seats_rolled_from_previous, 1)
        self.assertEqual(last_membership.workshops_without_admin_fee_rolled_over, None)
        self.assertEqual(last_membership.public_instructor_training_seats_rolled_over, None)
        self.assertEqual(last_membership.inhouse_instructor_training_seats_rolled_over, None)
        self.assertEqual(last_membership.rolled_from_membership, self.membership)
        self.assertEqual(last_membership.rolled_to_membership, None)

    def test_membership_rollover_negative_remaining_values(self):
        """If current membership has used more seats/workshops than allowed, and
        its remaining values are negative, the roll-over form should have max values
        for rolled-over fields set to 0, instead of these negative values.

        This is a regression test for https://github.com/carpentries/amy/issues/2056.
        """
        # Arrange

        self.setUpMembership(
            public_instructor_training_seats=0,
            inhouse_instructor_training_seats=0,
        )
        # add two instructor training seats, so the remaining seats will be -1
        event = Event.objects.create(
            slug="event-centrally-organised",
            host=self.org_beta,
            sponsor=self.org_beta,
            membership=self.membership,
            start=self.membership.agreement_start,
            end=self.membership.agreement_start + timedelta(days=1),
            administrator=self.dc,
        )
        Task.objects.bulk_create(
            [
                # public seat
                Task(
                    event=event,
                    person=self.hermione,
                    role=self.learner,
                    seat_membership=self.membership,
                    seat_public=True,
                ),
                # inhouse seat
                Task(
                    event=event,
                    person=self.harry,
                    role=self.learner,
                    seat_membership=self.membership,
                    seat_public=False,
                ),
            ]
        )

        # even though the remaining values are -1 (see assertion down below), the min
        # and max values will both be set to 0; previously the max value was set to the
        # remaining value, even if it was negative
        data = [
            (-1, "Ensure this value is greater than or equal to 0."),
            (1, "Ensure this value is less than or equal to 0."),
        ]

        for value, expected_msg in data:
            with self.subTest(value=value):
                payload = {
                    "name": "Test Membership",
                    # doesn't matter
                    "workshops_without_admin_fee_rolled_from_previous": 3,
                    "public_instructor_training_seats_rolled_from_previous": value,
                    "inhouse_instructor_training_seats_rolled_from_previous": value,
                    **self.data,
                }

                # Act
                response = self.client.post(
                    reverse("membership_create_roll_over", args=[self.membership.pk]),
                    data=payload,
                )

                # Assert
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.membership.public_instructor_training_seats_remaining, -1)
                self.assertEqual(self.membership.inhouse_instructor_training_seats_remaining, -1)
                for field in (
                    "public_instructor_training_seats_rolled_from_previous",
                    "inhouse_instructor_training_seats_rolled_from_previous",
                ):
                    self.assertEqual(
                        response.context["form"].fields[field].max_value,
                        0,
                    )
                    self.assertEqual(
                        response.context["form"].fields[field].min_value,
                        0,
                    )
                    self.assertEqual(
                        response.context["form"].errors[field],
                        [expected_msg],
                    )

    def test_membership_cannot_be_rolled_over_multiple_times(self):
        # Arrange
        self.setUpMembership()
        second_membership = Membership.objects.create(
            name="Test Membership2",
            consortium=False,
            public_status="public",
            variant="partner",
            agreement_start="2020-03-01",
            agreement_end="2021-03-01",
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=12,
            additional_public_instructor_training_seats=0,
            inhouse_instructor_training_seats=9,
            additional_inhouse_instructor_training_seats=0,
        )
        self.membership.rolled_to_membership = second_membership
        self.membership.save()

        # Act
        response = self.client.get(reverse("membership_create_roll_over", args=[self.membership.pk]))

        # Assert
        self.assertEqual(response.status_code, 404)
