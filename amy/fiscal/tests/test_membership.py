from datetime import timedelta, date
import itertools

from django.urls import reverse

from workshops.tests.base import TestBase
from workshops.models import Membership, Organization, Event, Role, Tag, Task


class TestMembership(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpTags()

        self.learner = Role.objects.get(name='learner')
        self.instructor = Role.objects.get(name='instructor')
        self.TTT = Tag.objects.get(name='TTT')

        # parametrize membership creation
        self.agreement_start = date(2018, 8, 2)
        self.agreement_start_next_day = self.agreement_start + timedelta(days=1)
        self.agreement_end = date(2018, 12, 31)
        self.workshop_interval = timedelta(days=13)

        # let's add a membership for one of the organizations
        self.current = Membership.objects.create(
            variant='partner',
            agreement_start=self.agreement_start,
            agreement_end=self.agreement_end,
            contribution_type='financial',
            workshops_without_admin_fee_per_agreement=10,
            self_organized_workshops_per_agreement=20,
            seats_instructor_training=25,
            additional_instructor_training_seats=3,
            organization=self.org_beta,
        )

        self_organized_admin = Organization.objects.get(domain='self-organized')

        # create a couple of workshops that span outside of agreement duration
        data = [
            [self.agreement_start - timedelta(days=180), self_organized_admin, None],
            [self.agreement_start - timedelta(days=1), self.org_beta, 500],
            [self.agreement_start - timedelta(days=1), self_organized_admin, None],
            [self.agreement_end + timedelta(days=1), self.org_beta, 500],
        ]
        for i, (start_date, admin, fee) in enumerate(data):
            Event.objects.create(
                slug='event-outside-agreement-range-{}'.format(i),
                host=self.org_beta,
                # create each event starts roughly month later
                start=start_date,
                end=start_date + timedelta(days=1),
                administrator=admin,
                admin_fee=fee,
            )

        # let's add a few events for that organization
        type_ = itertools.cycle(['self-organized', 'no-fee', 'self-organized'])
        for i in range(20):
            next_type = next(type_)
            e = None

            if next_type == 'self-organized':
                e = Event.objects.create(
                    slug='event-under-umbrella{}'.format(i),
                    host=self.org_beta,
                    # create each event starts roughly month later
                    start=self.agreement_start + i * self.workshop_interval,
                    end=self.agreement_start_next_day + i * self.workshop_interval,
                    administrator=self_organized_admin,
                )
                e.tags.set([self.TTT])

            elif next_type == 'no-fee':
                e = Event.objects.create(
                    slug='event-under-umbrella{}'.format(i),
                    host=self.org_beta,
                    # create each event starts roughly month later
                    start=self.agreement_start + i * self.workshop_interval,
                    end=self.agreement_start_next_day + i * self.workshop_interval,
                    # just to satisfy the criteria
                    administrator=self.org_beta,
                    admin_fee=0,
                )
                e.tags.set([self.TTT])

            # add a number of tasks for counting instructor training seats
            if e and i < 10:
                Task.objects.create(
                    event=e, person=self.admin,
                    role=self.learner,
                    seat_membership=self.current,
                )
            # add a number of tasks for counting instructor training seats, but
            # this time make these tasks instructor tasks - should not be
            # counted
            if e and i > 10:
                Task.objects.create(
                    event=e, person=self.admin,
                    role=self.instructor,
                    seat_membership=self.current,
                )
        # above code should create 11 events that start in 2018:
        # self-organized, no-fee, self-organized, self-organized, no-fee,
        # self-organized, self-organized, no-fee, self-organized,
        # self-organized, no-fee, self-organized,

    def test_multiple_memberships(self):
        """Ensure we can have multiple memberships (even overlapping)."""
        overlapping = Membership.objects.create(
            variant='partner',
            agreement_start=date(2015, 7, 1),
            agreement_end=date(2016, 6, 30),
            contribution_type='financial',
            workshops_without_admin_fee_per_agreement=10,
            self_organized_workshops_per_agreement=20,
            organization=self.org_beta,
        )

        self.assertIn(self.current, self.org_beta.membership_set.all())
        self.assertIn(overlapping, self.org_beta.membership_set.all())

    def test_workshops_without_admin_fee(self):
        """Ensure we calculate properly number of workshops per year."""
        self.assertEqual(
            self.current.workshops_without_admin_fee_per_agreement, 10)
        self.assertEqual(
            self.current.workshops_without_admin_fee_completed, 4)
        self.assertEqual(
            self.current.workshops_without_admin_fee_remaining, 6)

    def test_self_organized_workshops(self):
        """Ensure we calculate properly number of workshops per year."""
        self.assertEqual(
            self.current.self_organized_workshops_per_agreement, 20)
        self.assertEqual(
            self.current.self_organized_workshops_completed, 8)
        self.assertEqual(
            self.current.self_organized_workshops_remaining, 12)

    def test_delete_membership(self):
        '''Test that we can delete membership instance'''
        # first we need to remove all tasks refering to the membership
        Task.objects.all().delete()
        response = self.client.post(
            reverse('membership_delete', args=[self.current.pk]),
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('organization_details', args=[self.current.organization.domain]),
        )
        self.assertFalse(response.context['organization'].membership_set.all())
        self.assertEqual(response.context['organization'].membership_set.count(), 0)
        with self.assertRaises(Membership.DoesNotExist):
            self.current.refresh_from_db()

    def test_number_of_instructor_training_seats(self):
        """Ensure calculation of seats in the instructor training events is
        correct."""
        self.assertEqual(
            self.current.seats_instructor_training, 25
        )
        self.assertEqual(
            self.current.additional_instructor_training_seats, 3
        )
        self.assertEqual(
            self.current.seats_instructor_training_utilized, 10
        )
        self.assertEqual(
            self.current.seats_instructor_training_remaining, 18
        )
