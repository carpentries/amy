from django.urls import reverse

from workshops.models import Person
from workshops.tests.base import TestBase


class TestEmptyDuplicates(TestBase):
    """Tests to return empty context variables when no matches found."""
    def setUp(self):
        self._setUpUsersAndLogin()

        self.harry = Person.objects.create(
            personal='Harry', family='Potter', username='potter_harry',
            email='hp@hogwart.edu')
        self.kira = Person.objects.create(
            personal='Light', family='Yagami', username='light_yagami',
            email='ly@hogwart.edu')
        self.batman = Person.objects.create(
            personal='Bruce', family='Wayne', username='bruce_wayne',
            email='batman@waynecorp.com')
        self.ironman = Person.objects.create(
            personal='Tony', family='Stark', username='tony_stark',
            email='ironman@starkindustries.com')

        self.url = reverse('duplicate_persons')

    def test_switched_names_persons(self):
        """Ensure none of the above persons are in `switched_persons`."""
        rv = self.client.get(self.url)
        switched = rv.context['switched_persons']
        self.assertNotIn(self.harry, switched)
        self.assertNotIn(self.kira, switched)
        self.assertNotIn(self.batman, switched)
        self.assertNotIn(self.ironman, switched)

    def test_duplicate_persons(self):
        """Ensure none of the above persons are in `duplicate_persons`."""
        rv = self.client.get(self.url)
        switched = rv.context['duplicate_persons']
        self.assertNotIn(self.harry, switched)
        self.assertNotIn(self.kira, switched)
        self.assertNotIn(self.batman, switched)
        self.assertNotIn(self.ironman, switched)


class TestFindingDuplicates(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

        self.harry = Person.objects.create(
            personal='Harry', family='Potter', username='potter_harry',
            email='hp@hogwart.edu')
        self.potter = Person.objects.create(
            personal='Potter', family='Harry', username='harry_potter',
            email='hp+1@hogwart.edu')
        self.ron = Person.objects.create(
            personal='Ron', family='Weasley', username='weasley_ron',
            email='rw@hogwart.edu')
        self.ron2 = Person.objects.create(
            personal='Ron', family='Weasley', username='weasley_ron_2',
            email='rw+1@hogwart.edu')

        self.url = reverse('duplicate_persons')

    def test_switched_names_persons(self):
        rv = self.client.get(self.url)
        switched = rv.context['switched_persons']
        self.assertIn(self.harry, switched)
        self.assertIn(self.potter, switched)
        self.assertNotIn(self.ron, switched)
        self.assertNotIn(self.ron2, switched)

    def test_duplicate_persons(self):
        rv = self.client.get(self.url)
        switched = rv.context['duplicate_persons']
        self.assertIn(self.ron, switched)
        self.assertIn(self.ron2, switched)
        self.assertNotIn(self.harry, switched)
        self.assertNotIn(self.potter, switched)

    # there might be more to come
