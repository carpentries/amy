from django.core.urlresolvers import reverse

from ..models import Person
from .base import TestBase


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

        self.url = reverse('duplicates')

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
