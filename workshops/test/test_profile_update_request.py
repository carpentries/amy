from django.core.urlresolvers import reverse

from .base import TestBase
from ..models import ProfileUpdateRequest, Person, KnowledgeDomain, Lesson


class TestProfileUpdateRequest(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpLessons()
        self._setUpBadges()
        self._setUpInstructors()
        self._setUpUsersAndLogin()

    def test_request_added(self):
        """Test if ProfileUpdateRequest is successfully added."""
        data = {
            'recaptcha_response_field': 'PASSED',  # to auto-pass RECAPTCHA
            'personal': 'Harry', 'family': 'Potter',
            'email': 'harry@potter.com', 'airport_iata': 'LON',
            'affiliation': 'Auror at Ministry of Magic',
            'occupation': '', 'occupation_other': 'Auror',
            'github': 'hpotter', 'twitter': 'hpotter',
            'orcid': '', 'website': '', 'gender': 'M',
            'domains': [1, 2],  # IDs
            'lessons': [1, 2],  # IDs
        }
        rv = self.client.post(reverse('profileupdate_request'), data)
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert 'Fix errors below' not in content
        assert \
            'Thank you for updating your instructor profile' in content
        assert ProfileUpdateRequest.objects.all().count() == 1
        assert ProfileUpdateRequest.objects.all()[0].active is True

        # Not testing if emails are sent because we don't send them out for
        # profile updates for now.

    def test_request_discarded(self):
        """Ensure the request is discarded properly."""
        # add a minimal request
        pr = ProfileUpdateRequest.objects.create(
            personal='Harry', family='Potter', email='harry@potter.com',
            airport_iata='LON', affiliation='Hogwarts',
        )
        rv = self.client.get(reverse('profileupdaterequest_discard',
                                     args=[pr.pk]))
        assert rv.status_code == 302
        pr.refresh_from_db()
        assert not pr.active

    def test_request_match_person(self):
        "Check the details of ProfileUpdateRequest when it matches a Person."
        pr = ProfileUpdateRequest.objects.create(
            personal='Harry', family='Potter', email='harry@potter.com',
            airport_iata='LON', affiliation='Hogwarts', active=True,
        )
        rv = self.client.get(reverse('profileupdaterequest_details',
                                     args=[pr.pk]))
        content = rv.content.decode('utf-8')

        msg = ('No-one matches this email (harry@potter.com) '
               'or name (Harry Potter).')
        assert msg not in content
        assert rv.context['old']  # 'old' contains person from the DB

    def test_request_not_match(self):
        """Check the details of ProfileUpdateRequest when it doesn't match any
        Person."""
        pr = ProfileUpdateRequest.objects.create(
            personal='Warry', family='Trotter', email='warry@trotter.com',
            airport_iata='LON', affiliation='Hogwarts', active=True,
        )
        rv = self.client.get(reverse('profileupdaterequest_details',
                                     args=[pr.pk]))
        content = rv.content.decode('utf-8')

        msg = ('No-one matches this email (warry@trotter.com) '
               'or name (Warry Trotter).')
        assert msg in content
        assert not rv.context['old']  # 'old' contains person from the DB

    def test_request_accepted(self):
        """Ensure ProfileUpdateRequest gets rewritten correctly to the selected
        Person."""
        person = Person.objects.get(personal='Harry', family='Potter')
        pr = ProfileUpdateRequest.objects.create(
            active=True,
            personal='Warry', family='Trotter', email='warry@trotter.com',
            affiliation='Auror at Ministry of Magic', airport_iata='AAA',
            occupation='', occupation_other='Auror',
            github='hpotter', twitter='hpotter',
            orcid='0000-1111', website='http://warry.trotter.com/', gender='M',
        )
        pr.domains.add(*KnowledgeDomain.objects.all()[0:2]),
        pr.lessons.add(*Lesson.objects.all()[0:2]),
        rv = self.client.get(reverse('profileupdaterequest_accept',
                                     args=[pr.pk, person.pk]))
        assert rv.status_code == 302, rv.status_code

        person.refresh_from_db()
        assert person.personal == 'Warry'
        assert person.family == 'Trotter'
        assert person.email == 'warry@trotter.com'
        assert person.affiliation == 'Auror at Ministry of Magic'
        assert person.airport.iata == 'AAA'
        assert person.github == person.twitter == 'hpotter'
        assert person.url == 'http://warry.trotter.com/'
        assert person.gender == 'M'
        assert person.occupation == 'Auror'
        assert person.orcid == '0000-1111'
        assert set(person.domains.all()) == \
            set(KnowledgeDomain.objects.all()[0:2])
        assert set(person.lessons.all()) == set(Lesson.objects.all()[0:2])

    def test_incomplete_selection_of_matching_person(self):
        """Regression test: no 500 when incomplete form submitted to select
        a matching person."""
        pr = ProfileUpdateRequest.objects.create(
            active=True,
            personal='Warry', family='Trotter', email='warry@trotter.com',
            affiliation='Auror at Ministry of Magic', airport_iata='AAA',
            occupation='', occupation_other='Auror',
            github='hpotter', twitter='hpotter',
            orcid='0000-1111', website='http://warry.trotter.com/', gender='M',
        )
        pr.domains.add(*KnowledgeDomain.objects.all()[0:2]),
        pr.lessons.add(*Lesson.objects.all()[0:2]),
        url = (reverse('profileupdaterequest_details', args=[pr.pk]) +
               '?person_0=inigo&person_1=&submit=Submit')
        rv = self.client.get(url)
        self.assertNotEqual(rv.status_code, 500)

    def test_request_accepted_new_person_added(self):
        """Ensure new person is added when no-one matches the profile update
        request."""
        Person.objects.exclude(username='admin').delete()
        self.assertEqual(Person.objects.count(), 1)

        pr = ProfileUpdateRequest.objects.create(
            active=True,
            personal='Warry', family='Trotter', email='warry@trotter.com',
            affiliation='Auror at Ministry of Magic', airport_iata='AAA',
            occupation='', occupation_other='Auror',
            github='hpotter', twitter='hpotter',
            orcid='0000-1111', website='http://warry.trotter.com/', gender='M',
        )
        pr.domains.add(*KnowledgeDomain.objects.all()[0:2]),
        pr.lessons.add(*Lesson.objects.all()[0:2]),
        rv = self.client.get(reverse('profileupdaterequest_accept',
                                     args=[pr.pk]))
        self.assertEqual(rv.status_code, 302, rv.status_code)

        self.assertEqual(Person.objects.count(), 2)
        person = Person.objects.get(personal='Warry', family='Trotter')
        self.assertEqual(person.personal, 'Warry')
        self.assertEqual(person.family, 'Trotter')
        self.assertEqual(person.email, 'warry@trotter.com')
        self.assertEqual(person.affiliation, 'Auror at Ministry of Magic')
        self.assertEqual(person.airport.iata, 'AAA')
        self.assertEqual(person.github, 'hpotter')
        self.assertEqual(person.twitter, 'hpotter')
        self.assertEqual(person.url, 'http://warry.trotter.com/')
        self.assertEqual(person.gender, 'M')
        self.assertEqual(person.occupation, 'Auror')
        self.assertEqual(person.orcid, '0000-1111')
        self.assertEqual(set(person.domains.all()),
                         set(KnowledgeDomain.objects.all()[0:2]))
        self.assertEqual(set(person.lessons.all()),
                         set(Lesson.objects.all()[0:2]))


class TestProfileUpdateRequestsViews(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpLessons()
        self._setUpBadges()
        self._setUpInstructors()
        self._setUpUsersAndLogin()

        self.pur1 = ProfileUpdateRequest.objects.create(
            active=True, personal="Harry", family="Potter",
            email="harry@potter.com", airport_iata='AAA',
            affiliation='Hogwarts',
        )
        self.pur2 = ProfileUpdateRequest.objects.create(
            active=False, personal="Harry", family="Potter",
            email="harry@potter.com", airport_iata='AAA',
            affiliation='Hogwarts',
        )

    def test_active_requests_list(self):
        rv = self.client.get(reverse('all_profileupdaterequests'))
        assert self.pur1 in rv.context['object_list']
        assert self.pur2 not in rv.context['object_list']

    def test_inactive_requests_list(self):
        rv = self.client.get(reverse('all_closed_profileupdaterequests'))
        assert self.pur1 not in rv.context['object_list']
        assert self.pur2 in rv.context['object_list']

    def test_active_request_view(self):
        rv = self.client.get(reverse('profileupdaterequest_details',
                                     args=[self.pur1.pk]))
        assert rv.status_code == 200

    def test_inactive_request_view(self):
        rv = self.client.get(reverse('profileupdaterequest_details',
                                     args=[self.pur2.pk]))
        assert rv.status_code == 200

    def test_active_request_accept(self):
        rv = self.client.get(reverse('profileupdaterequest_accept',
                                     args=[self.pur1.pk, self.harry.pk]),
                             follow=True)
        assert rv.status_code == 200

    def test_inactive_request_accept(self):
        rv = self.client.get(reverse('profileupdaterequest_accept',
                                     args=[self.pur2.pk, self.harry.pk]),
                             follow=True)
        assert rv.status_code != 200

    def test_active_request_discard(self):
        rv = self.client.get(reverse('profileupdaterequest_discard',
                                     args=[self.pur1.pk]), follow=True)
        assert rv.status_code == 200

    def test_inactive_request_discard(self):
        rv = self.client.get(reverse('profileupdaterequest_discard',
                                     args=[self.pur2.pk]), follow=True)
        assert rv.status_code != 200
