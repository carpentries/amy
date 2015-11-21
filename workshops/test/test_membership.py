import datetime

from django.core.urlresolvers import reverse

from ..models import Event, Task, Role, Badge, Award
from ..util import get_members, get_membership_cutoff
from .base import TestBase


class TestMembership(TestBase):
    '''Tests for SCF membership.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

        one_day = datetime.timedelta(days=1)
        one_month = datetime.timedelta(days=30)
        three_years = datetime.timedelta(days=3 * 365)

        today = datetime.date.today()
        yesterday = today - one_day
        tomorrow = today + one_day
        
        earliest, latest = get_membership_cutoff()

        # Set up events in the past, at present, and in future.
        past = Event.objects.create(
            host=self.host_alpha,
            slug="in-past",
            start=today - three_years,
            end=tomorrow - three_years
        )

        present = Event.objects.create(
            host=self.host_alpha,
            slug="at-present",
            start=today - one_month
        )

        future = Event.objects.create(
            host=self.host_alpha,
            slug="in-future",
            start=today + one_month,
            end=tomorrow + one_month
        )

        # Roles and badges.
        instructor_role = Role.objects.create(name='instructor')
        member_badge = Badge.objects.create(name='member')

        # Spiderman is an explicit member.
        Award.objects.create(person=self.spiderman, badge=member_badge,
                             awarded=yesterday)

        # Hermione teaches in the past, now, and in future, so she's a member.
        Task.objects.create(event=past, person=self.hermione,
                            role=instructor_role)
        Task.objects.create(event=present, person=self.hermione,
                            role=instructor_role)
        Task.objects.create(event=future, person=self.hermione,
                            role=instructor_role)

        # Ron only teaches in the distant past, so he's not a member.
        Task.objects.create(event=past, person=self.ron,
                            role=instructor_role)

        # Harry only teaches in the future, so he's not a member.
        Task.objects.create(event=future, person=self.harry,
                            role=instructor_role)


    def test_members_default_cutoffs(self):
        "Make sure default membership rules are obeyed."

        members = get_members()
        self.assertTrue(len(members) == 2)
        self.assertTrue(self.hermione in members) # taught recently
        self.assertTrue(self.ron not in members) # taught too long ago
        self.assertTrue(self.harry not in members) # only teaching in the future
        self.assertTrue(self.spiderman in members) # explicit member


    def test_members_explicit_earliest(self):
        "Make sure membership rules are obeyed with explicit earliest date."

        # Set start date to exclude Hermione.
        members = get_members(datetime.date.today() - datetime.timedelta(days=1))
        self.assertTrue(len(members) == 1)
        self.assertTrue(self.hermione not in members) # taught recently
        self.assertTrue(self.ron not in members) # taught too long ago
        self.assertTrue(self.harry not in members) # only teaching in the future
        self.assertTrue(self.spiderman in members) # explicit member
