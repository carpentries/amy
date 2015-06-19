from django.core.urlresolvers import reverse

from ..models import Airport, Person
from .base import TestBase


class TestAirport(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_airport_delete(self):
        """Make sure deleted airport is longer accessible.

        Additionally check on_delete behavior for Person."""
        L1 = [
            self.airport_0_0.iata,
            self.airport_0_50.iata,
            self.airport_50_100.iata,
            self.airport_55_105.iata,
        ]
        L2 = [
            self.hermione.pk,
            self.harry.pk,
            self.ron.pk,
        ]

        for iata in L1[:3]:
            rv = self.client.get(reverse('airport_delete', args=[iata, ]))
            content = rv.content.decode('utf-8')
            assert 'Failed to delete' in content

        for person_pk in L2:
            Person.objects.get(pk=person_pk).delete()

        for iata in L1:
            rv = self.client.get(reverse('airport_delete', args=[iata, ]))
            assert rv.status_code == 302

            with self.assertRaises(Airport.DoesNotExist):
                Airport.objects.get(iata=iata)
