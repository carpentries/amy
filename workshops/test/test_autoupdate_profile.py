from django.core.urlresolvers import reverse

from workshops.models import Person, Qualification, KnowledgeDomain
from workshops.test import TestBase


class TestAutoUpdateProfile(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpLessons()
        self._setUpLanguages()

        self.user = Person.objects.create_user(
            username='user', personal='', family='',
            email='user@example.org', password='pass')

        Qualification.objects.create(person=self.user, lesson=self.git)
        Qualification.objects.create(person=self.user, lesson=self.sql)

        self.physics = KnowledgeDomain.objects.create(name='physics')
        self.chemistry = KnowledgeDomain.objects.create(name='chemistry')
        self.user.domains.add(self.physics)

        self.user.languages.add(self.english)
        self.user.languages.add(self.french)

        self.client.login(username='user', password='pass')

    def test_load_form(self):
        rv = self.client.get(reverse('autoupdate_profile'))
        self.assertEqual(rv.status_code, 200)

    def test_update_profile(self):
        data = {
            'personal': 'admin',
            'middle': '',
            'family': 'Smith',
            'email': 'admin@example.org',
            'gender': Person.UNDISCLOSED,
            'may_contact': True,
            'airport': self.airport_0_0.pk,
            'github': 'changed',
            'twitter': '',
            'url': '',
            'username': 'changed',
            'affiliation': '',
            'languages_1': [self.latin.pk, self.french.pk],
            'domains': [self.chemistry.pk],
            'lessons': [self.git.pk, self.matlab.pk],
            'privacy_consent': True,
        }

        rv = self.client.post(reverse('autoupdate_profile'), data, follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self.assertNotIn('Fix errors below', content)
        self.user.refresh_from_db()

        self.assertEqual(self.user.username, 'user')  # username is read-only
        self.assertEqual(self.user.github, None)  # github is read-only
        self.assertEqual(self.user.family, 'Smith')
        self.assertEqual(set(self.user.lessons.all()),
                         {self.git, self.matlab})
        self.assertEqual(list(self.user.domains.all()), [self.chemistry])
        self.assertEqual(set(self.user.languages.all()),
                         {self.french, self.latin})
