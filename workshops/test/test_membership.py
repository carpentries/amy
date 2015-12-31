from datetime import timedelta, date
import itertools

from .base import TestBase
from ..models import Membership, Host, Event


class TestMembership(TestBase):
    def setUp(self):
        super().setUp()

        # let's add a membership for one of the hosts
        self.current = Membership.objects.create(
            variant='partner',
            agreement_start=date(2015, 1, 1),
            agreement_end=date(2015, 12, 31),
            contribution_type='financial',
            workshops_without_admin_fee_per_year=10,
            self_organized_workshops_per_year=20,
            host=self.host_beta,
        )

        self_organized_admin = Host.objects.get(domain='self-organized')

        # let's add a few events for that host
        type_ = itertools.cycle(['self-organized', 'no-fee', 'self-organized'])
        for i in range(20):
            next_type = next(type_)

            if next_type == 'self-organized':
                Event.objects.create(
                    slug='event-under-umbrella{}'.format(i),
                    host=self.host_beta,
                    # create each event starts roughly month later
                    start=date(2015, 1, 1) + i * timedelta(days=31),
                    end=date(2015, 1, 2) + i * timedelta(days=31),
                    administrator=self_organized_admin,
                )

            elif next_type == 'no-fee':
                Event.objects.create(
                    slug='event-under-umbrella{}'.format(i),
                    host=self.host_beta,
                    # create each event starts roughly month later
                    start=date(2015, 1, 1) + i * timedelta(days=31),
                    end=date(2015, 1, 2) + i * timedelta(days=31),
                    # just to satisfy the criteria
                    administrator=self.host_beta,
                    admin_fee=0,
                )
        # above code should create 11 events that start in 2015:
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
            workshops_without_admin_fee_per_year=10,
            self_organized_workshops_per_year=20,
            host=self.host_beta,
        )

        self.assertIn(self.current, self.host_beta.membership_set.all())
        self.assertIn(overlapping, self.host_beta.membership_set.all())

    def test_workshops_without_admin_fee(self):
        """Ensure we calculate properly number of workshops per year."""
        self.assertEqual(
            self.current.workshops_without_admin_fee_per_year, 10)
        self.assertEqual(
            self.current.workshops_without_admin_fee_per_year_completed, 4)
        self.assertEqual(
            self.current.workshops_without_admin_fee_per_year_remaining, 6)

    def test_self_organized_workshops(self):
        """Ensure we calculate properly number of workshops per year."""
        self.assertEqual(
            self.current.self_organized_workshops_per_year, 20)
        self.assertEqual(
            self.current.self_organized_workshops_per_year_completed, 8)
        self.assertEqual(
            self.current.self_organized_workshops_per_year_remaining, 12)
