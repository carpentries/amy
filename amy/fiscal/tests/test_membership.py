from datetime import timedelta, date
from typing import List

from django.urls import reverse
from django_comments.models import Comment

from fiscal.forms import (
    MembershipCreateForm,
    MembershipForm,
    MembershipExtensionForm,
)
from workshops.tests.base import TestBase
from workshops.models import (
    Membership,
    Organization,
    Event,
    Role,
    Tag,
    Task,
    MemberRole,
    Member,
)


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
            self_organized_workshops_per_agreement=20,
            seats_instructor_training=25,
            additional_instructor_training_seats=3,
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
            self_organized_workshops_per_agreement=20,
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
        self.assertEqual(self.current.workshops_without_admin_fee_completed, 6)
        self.assertEqual(self.current.workshops_without_admin_fee_planned, 4)
        self.assertEqual(self.current.workshops_without_admin_fee_remaining, 0)

    def test_self_organized_workshops(self):
        """Ensure we calculate properly number of workshops per year."""
        self.setUpTasks()
        self.assertEqual(self.current.self_organized_workshops_per_agreement, 20)
        self.assertEqual(self.current.self_organized_workshops_completed, 6)
        self.assertEqual(self.current.self_organized_workshops_planned, 4)
        self.assertEqual(self.current.self_organized_workshops_remaining, 10)

    def test_delete_membership(self):
        """Test that we can delete membership instance"""
        response = self.client.post(
            reverse("membership_delete", args=[self.current.pk])
        )
        self.assertRedirects(response, reverse("all_memberships"))

        # self.assertEqual(self.org_beta.memberships.count(), 0)
        with self.assertRaises(Membership.DoesNotExist):
            self.current.refresh_from_db()

    def test_number_of_instructor_training_seats(self):
        """Ensure calculation of seats in the instructor training events is
        correct."""
        self.setUpTasks()
        self.assertEqual(self.current.seats_instructor_training, 25)
        self.assertEqual(self.current.additional_instructor_training_seats, 3)
        self.assertEqual(self.current.seats_instructor_training_utilized, 5)
        self.assertEqual(self.current.seats_instructor_training_remaining, 23)


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
            self_organized_workshops_per_agreement=8,
            self_organized_workshops_rolled_from_previous=4,
            self_organized_workshops_rolled_over=5,
            seats_instructor_training=6,
            additional_instructor_training_seats=4,
            instructor_training_seats_rolled_from_previous=2,
            instructor_training_seats_rolled_over=5,
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
                    start=date.today() + timedelta(days=1),
                    end=date.today() + timedelta(days=2),
                    administrator=administrator,
                )
                for i in range(count)
            ]
            planned_events = Event.objects.bulk_create(planned_events)
            events += planned_events

        return events

    def setUpTasks(self, count: int) -> List[Task]:
        tasks = self.membership.task_set.bulk_create(
            [
                Task(
                    role=self.learner,
                    person=self.admin,
                    event=Event.objects.create(
                        slug=f"event-learner-{i}",
                        host=self.dc,
                        administrator=self.org_alpha,
                    ),
                    seat_membership=self.membership,
                )
                for i in range(count)
            ]
        )
        return tasks


class TestMembershipConsortiumCountingCentrallyOrganisedWorkshops(
    TestMembershipConsortiumCountingBase
):
    def test_cancelled_workshops_are_not_counted(self):
        self.setUpWorkshops("cancelled", count=2)
        self.assert_(Event.objects.all())
        self.assertEqual(
            list(self.membership._workshops_without_admin_fee_queryset()), []
        )

    def test_self_organised_workshops_are_not_counted(self):
        self.setUpWorkshops("self-organised", count=2)
        self.assert_(Event.objects.all())
        self.assertEqual(
            list(self.membership._workshops_without_admin_fee_queryset()), []
        )

    def test_completed_workshops(self):
        self.setUpWorkshops("completed", count=3)
        self.assert_(Event.objects.all())
        self.assertEqual(self.membership.workshops_without_admin_fee_completed, 3)

    def test_planned_workshops(self):
        self.setUpWorkshops("planned", count=4)
        self.assert_(Event.objects.all())
        self.assertEqual(self.membership.workshops_without_admin_fee_planned, 4)

    def test_remaining_workshops(self):
        self.setUpWorkshops(
            "cancelled", "self-organised", "completed", "planned", count=2
        )
        self.assert_(Event.objects.all())
        # number of available: 10 + 2 - 5 = 7
        # number of workshops counted: 2 * completed + 2 * planned
        self.assertEqual(self.membership.workshops_without_admin_fee_remaining, 3)


class TestMembershipConsortiumCountingSelfOrganisedWorkshops(
    TestMembershipConsortiumCountingBase
):
    def test_cancelled_workshops_are_not_counted(self):
        self.setUpWorkshops("cancelled", count=2, administrator=self.self_organized)
        self.assert_(Event.objects.all())
        self.assertEqual(list(self.membership._self_organized_workshops_queryset()), [])

    def test_centrally_organised_workshops_are_not_counted(self):
        self.setUpWorkshops("completed", count=2, administrator=self.dc)
        self.assert_(Event.objects.all())
        self.assertEqual(list(self.membership._self_organized_workshops_queryset()), [])

    def test_completed_workshops(self):
        self.setUpWorkshops("completed", count=3, administrator=self.self_organized)
        self.assert_(Event.objects.all())
        self.assertEqual(self.membership.self_organized_workshops_completed, 3)

    def test_planned_workshops(self):
        self.setUpWorkshops("planned", count=4, administrator=self.self_organized)
        self.assert_(Event.objects.all())
        self.assertEqual(self.membership.self_organized_workshops_planned, 4)

    def test_remaining_workshops(self):
        self.setUpWorkshops(
            "cancelled",
            "self-organised",
            "completed",
            "planned",
            count=2,
            administrator=self.self_organized,
        )
        self.assert_(Event.objects.all())
        # number of available: 8 + 4 - 5 = 7
        # number of workshops counted: 2 * self-org + 2 * completed + 2 * planned
        self.assertEqual(self.membership.self_organized_workshops_remaining, 1)


class TestMembershipConsortiumCountingInstructorTrainingSeats(
    TestMembershipConsortiumCountingBase
):
    def test_seats_total(self):
        # rolled from previous aren't counted into the total
        self.assertEqual(self.membership.seats_instructor_training_total, 10)

    def test_seats_utilized(self):
        self.setUpTasks(count=5)
        self.assertEqual(self.membership.seats_instructor_training_utilized, 5)

    def test_seats_remaining(self):
        self.setUpTasks(count=5)
        # total and rolled over from previous: 10 + 2
        # utilized: 5
        # rolled-over: 5
        # remaining: 2
        self.assertEqual(self.membership.seats_instructor_training_remaining, 2)


class TestMembershipForms(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpTags()

    def test_creating_membership_with_no_comment(self):
        """Ensure that no comment is added when MembershipCreateForm without
        comment content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 28),
            "agreement_end": date(2022, 1, 28),
            "variant": "partner",
            "contribution_type": "financial",
            "additional_instructor_training_seats": 0,
            "seats_instructor_training": 0,
            "comment": "",
        }
        form = MembershipCreateForm(data)
        form.save()
        self.assertEqual(Comment.objects.count(), 0)

    def test_creating_membership_with_comment(self):
        """Ensure that a comment is added when MembershipCreateForm with
        comment content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 28),
            "agreement_end": date(2022, 1, 28),
            "variant": "partner",
            "contribution_type": "financial",
            "additional_instructor_training_seats": 0,
            "seats_instructor_training": 0,
            "comment": "This is a test comment.",
        }
        form = MembershipCreateForm(data)
        obj = form.save()
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.comment, "This is a test comment.")
        self.assertIn(comment, Comment.objects.for_model(obj))

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
            self_organized_workshops_per_agreement=20,
            seats_instructor_training=25,
            additional_instructor_training_seats=3,
        )
        Member.objects.create(
            membership=membership,
            organization=self.org_beta,
            role=MemberRole.objects.first(),
        )

        self.assertNotIn("comment", MembershipForm.Meta.fields)

        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 28),
            "agreement_end": date(2022, 1, 28),
            "variant": "partner",
            "contribution_type": "financial",
            "additional_instructor_training_seats": 0,
            "seats_instructor_training": 0,
        }
        form = MembershipForm(data, instance=membership)
        form.save()
        self.assertEqual(Comment.objects.count(), 0)

    def test_membership_agreement_dates_validation(self):
        """Validate invalid agreement end date (can't be sooner than start date)."""
        data = {
            "main_organization": self.org_alpha.pk,
            "name": "Test Membership",
            "consortium": False,
            "public_status": "public",
            "agreement_start": date(2021, 1, 26),
            "agreement_end": date(2020, 1, 26),
            "variant": "partner",
            "contribution_type": "financial",
            "additional_instructor_training_seats": 0,
            "seats_instructor_training": 0,
        }
        form = MembershipForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["agreement_end"],
            ["Agreement end date can't be sooner than the start date."],
        )


class TestNewMembershipWorkflow(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def setUpMembership(self, consortium: bool):
        self.membership = Membership.objects.create(
            name="Test Membership",
            consortium=consortium,
            public_status="public",
            variant="partner",
            agreement_start="2021-02-14",
            agreement_end="2022-02-14",
            contribution_type="financial",
            seats_instructor_training=0,
            additional_instructor_training_seats=0,
        )
        self.member_role = MemberRole.objects.first()

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
            "contribution_type": "financial",
            "seats_instructor_training": 0,
            "additional_instructor_training_seats": 0,
        }
        response = self.client.post(reverse("membership_add"), data=data)
        latest_membership = Membership.objects.order_by("-id").first()

        self.assertRedirects(
            response, reverse("membership_details", args=[latest_membership.pk])
        )

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
            "contribution_type": "financial",
            "seats_instructor_training": 0,
            "additional_instructor_training_seats": 0,
        }
        response = self.client.post(reverse("membership_add"), data=data)
        latest_membership = Membership.objects.order_by("-id").first()

        self.assertRedirects(
            response, reverse("membership_members", args=[latest_membership.pk])
        )

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
            "contribution_type": "financial",
            "seats_instructor_training": 0,
            "additional_instructor_training_seats": 0,
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
            "contribution_type": "financial",
            "seats_instructor_training": 0,
            "additional_instructor_training_seats": 0,
        }
        response = self.client.post(reverse("membership_add"), data=data, follow=True)

        latest_membership = Membership.objects.order_by("-id").first()
        self.assertEqual(response.context["membership"], latest_membership)
        self.assertEqual(latest_membership.member_set.count(), 1)
        member = latest_membership.member_set.first()
        self.assertEqual(member.role.name, "contract_signatory")
        self.assertEqual(member.organization, self.org_alpha)

    def test_adding_new_member_to_nonconsortium(self):
        """Ensure only 1 member can be added to non-consortium membership."""
        self.setUpMembership(consortium=False)
        self.assertEqual(self.membership.member_set.count(), 0)

        # only 1 member allowed
        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-organization": self.org_alpha.pk,
            "form-0-role": self.member_role.pk,
            "form-0-id": "",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )
        self.assertEqual(self.membership.member_set.count(), 1)
        self.assertEqual(list(self.membership.organizations.all()), [self.org_alpha])

        # posting this will fail because only 1 form in the formset is allowed
        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-organization": self.org_alpha.pk,
            "form-0-role": self.member_role.pk,
            "form-0-id": "",
            "form-1-organization": self.org_beta.pk,
            "form-1-role": self.member_role.pk,
            "form-1-id": "",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.membership.member_set.count(), 1)  # number didn't change

    def test_adding_new_members_to_consortium(self):
        """Ensure 1+ members can be added to consortium membership."""
        self.setUpMembership(consortium=True)
        self.assertEqual(self.membership.member_set.count(), 0)
        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-organization": self.org_alpha.pk,
            "form-0-role": self.member_role.pk,
            "form-0-id": "",
            "form-1-organization": self.org_beta.pk,
            "form-1-role": self.member_role.pk,
            "form-1-id": "",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )
        self.assertEqual(self.membership.member_set.count(), 2)
        self.assertEqual(
            list(self.membership.organizations.all()), [self.org_alpha, self.org_beta]
        )

    def test_removing_members_from_nonconsortium(self):
        """Ensure removing the only member from non-consortium membership is not
        allowed."""
        self.setUpMembership(consortium=False)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-organization": m1.organization.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
            "form-0-DELETE": "on",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)  # response failed
        self.assertEqual(list(self.membership.organizations.all()), [self.org_alpha])

    def test_removing_members_from_consortium(self):
        """Ensure removing all members from consortium membership is allowed."""
        self.setUpMembership(consortium=True)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )
        m2 = Member.objects.create(
            organization=self.org_beta,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 2,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-organization": m1.organization.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
            "form-0-DELETE": "on",
            "form-1-organization": m2.organization.pk,
            "form-1-role": m2.role.pk,
            "form-1-id": m2.pk,
            "form-1-DELETE": "on",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )
        self.assertEqual(list(self.membership.organizations.all()), [])

    def test_mix_adding_removing_members_from_consortium(self):
        """Ensure a mixed-content formset for consortium membership members works
        fine (e.g. a new member is added, and an old one is removed)."""
        self.setUpMembership(consortium=True)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-organization": m1.organization.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
            "form-0-DELETE": "on",
            "form-1-organization": self.org_beta.pk,
            "form-1-role": self.member_role.pk,
            "form-1-id": "",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )

        self.assertEqual(list(self.membership.organizations.all()), [self.org_beta])


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
            "new_agreement_end": "invalid value",
            # field accepted
            "extension": "1",
        }

        form = MembershipExtensionForm(data)

        self.assertTrue(form.is_valid())

    def test_form_validating_extension(self):
        data = [
            ("string", False),
            ("", False),
            ("-1", False),
            ("0", False),
            ("1", True),
            ("2", True),
        ]
        for extension, valid in data:
            with self.subTest(extension=extension, valid=valid):
                form = MembershipExtensionForm(dict(extension=extension))
                self.assertEqual(form.is_valid(), valid)

    def test_membership_extended(self):
        membership = Membership.objects.create(
            name="Test Membership",
            consortium=False,
            public_status="public",
            variant="partner",
            agreement_start="2020-03-01",
            agreement_end="2021-03-01",
            extended=None,
            contribution_type="financial",
            seats_instructor_training=0,
            additional_instructor_training_seats=0,
        )
        Member.objects.create(
            organization=self.org_alpha,
            membership=membership,
            role=MemberRole.objects.first(),
        )
        data = {"extension": 30}

        response = self.client.post(
            reverse("membership_extend", args=[membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[membership.pk])
        )
        membership.refresh_from_db()
        self.assertEqual(membership.extended, 30)
        self.assertEqual(membership.agreement_end, date(2021, 3, 31))
