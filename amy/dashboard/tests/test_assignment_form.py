from django.contrib.auth.models import Group
from django.test import TestCase

from dashboard.forms import AssignmentForm
from workshops.models import Person


class TestAssignmentForm(TestCase):
    def setUp(self):
        self.superuser = Person.objects.create(
            personal="Harry",
            family="Potter",
            email="hp@magic.uk",
            username="potter_harry",
            is_superuser=True,
        )
        self.administrator = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="weasley_ron",
        )
        self.both = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hg@magic.uk",
            username="granger_hermione",
            is_superuser=True,
        )

    def test_assigned_to_queryset(self):
        """Ensure duplicate results don't appear in the queryset.

        This is a regression test for https://github.com/carpentries/amy/issues/1792.
        """
        admins = Group.objects.get(name="administrators")
        committee = Group.objects.get(name="steering committee")
        self.administrator.groups.add(admins)
        # user has to be in 2 groups to yield duplicate
        # results in the queryset
        self.both.groups.add(committee)
        self.both.groups.add(admins)

        field = AssignmentForm().fields["assigned_to"]
        self.assertEqual(
            list(field.queryset), [self.both, self.superuser, self.administrator]
        )
