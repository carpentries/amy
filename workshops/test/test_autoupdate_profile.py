from django.core.urlresolvers import reverse

from workshops.models import Person, Lesson, Qualification
from workshops.test import TestBase


class TestAutoUpdateProfile(TestBase):
    def setUp(self):
        self._setUpAirports()
        self.user = Person.objects.create_user(
            username='user', personal='', family='',
            email='user@example.org', password='pass')
        self.python = Lesson.objects.create(name='swc/python')
        self.shell = Lesson.objects.create(name='swc/shell')
        self.matlab = Lesson.objects.create(name='swc/matlab')
        self.git = Lesson.objects.create(name='swc/r')
        Qualification.objects.create(person=self.user, lesson=self.python)
        Qualification.objects.create(person=self.user, lesson=self.shell)
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
            'domains': [],
            'lessons': [self.python.pk, self.matlab.pk],
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
                         {self.python, self.matlab})
