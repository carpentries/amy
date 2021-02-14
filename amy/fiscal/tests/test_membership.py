from datetime import timedelta, date

from django.urls import reverse
from django_comments.models import Comment

from fiscal.forms import MembershipCreateForm, MembershipForm
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

    def setUpMembership(self):
        self.membership = Membership.objects.create(
            public_status="public",
            variant="partner",
            agreement_start="2021-02-14",
            agreement_end="2022-02-14",
            contribution_type="financial",
            seats_instructor_training=0,
            additional_instructor_training_seats=0,
        )
        self.member_role = MemberRole.objects.first()

    def test_new_membership_redirects_to_members(self):
        data = {
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

    def test_new_membership_has_no_members(self):
        data = {
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
        self.assertEqual(latest_membership.member_set.count(), 0)

    def test_adding_new_members(self):
        self.setUpMembership()
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
