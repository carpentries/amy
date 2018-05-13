from django.urls import reverse

from ..models import Airport, Person
from .base import TestBase


class TestAirport(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_airport_details(self):
        """Regression test: ensure airport details page renders correctly."""
        rv = self.client.get(reverse('airport_details', args=['AAA']))
        self.assertEqual(rv.status_code, 200)

    def test_airport_delete(self):
        """Make sure deleted airport is no longer accessible.."""
        airports = [
            self.airport_0_0.iata,
            self.airport_0_50.iata,
            self.airport_50_100.iata,
            self.airport_55_105.iata,
            self.airport_0_10.iata,
        ]
        can_be_removed = [
            False,
            False,
            False,
            False,
            True,
        ]
        people = [
            self.hermione.pk,
            self.harry.pk,
            self.ron.pk,
            self.spiderman.pk,
            self.ironman.pk,
            self.blackwidow.pk,
        ]

        # airports 0_0, 0_50, 50_100, 55_105 cannot be removed because they're
        # referenced by instructors and/or non-instructors
        for iata, remove in zip(airports, can_be_removed):
            rv = self.client.post(reverse('airport_delete', args=[iata, ]))
            if remove:
                self.assertEqual(rv.status_code, 302)
            else:
                self.assertEqual(rv.status_code, 200)
                content = rv.content.decode('utf-8')
                self.assertIn('Failed to delete', content)

        # unassign airports from people
        Person.objects.filter(pk__in=people).update(airport=None)

        # now all airports can be removed, except for airport that has been
        # removed
        for iata, remove in zip(airports, can_be_removed):
            if remove:
                continue

            rv = self.client.post(reverse('airport_delete', args=[iata, ]))
            self.assertEqual(rv.status_code, 302)

            with self.assertRaises(Airport.DoesNotExist):
                Airport.objects.get(iata=iata)

    def test_airport_ordering(self):
        """Make sure that airports are listed in alphabetical order.
        See #1193."""
        first_airport = Airport.objects.all()[0]
        assert first_airport.iata == 'AAA'
