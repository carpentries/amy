from unittest.mock import patch

from django.core import mail
from django.urls import reverse

from workshops.tests.base import TestBase
from workshops.models import (
    ProfileUpdateRequest,
    Person,
    Task,
    Award,
    Airport,
    Qualification,
    KnowledgeDomain,
    Lesson,
    Airport,
)


class TestProfileUpdateRequest(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpLessons()
        self._setUpBadges()
        self._setUpInstructors()
        self._setUpUsersAndLogin()

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
               '?person=&submit=Submit')
        rv = self.client.get(url)
        self.assertNotEqual(rv.status_code, 500)

    def test_request_accepted_new_person_added(self):
        """Ensure new person is added when no-one matches the profile update
        request."""
        # remove some dependant objects first
        Task.objects.all().delete()
        Award.objects.all().delete()
        Person.objects.all().update(airport=None)
        Qualification.objects.all().delete()
        # now remove all persons except for admin
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

    def test_database_constraints_when_updating(self):
        """Ensure unique constraints are checked when processing a profile
        update.

        This is a regression test for #1237:
        https://github.com/swcarpentry/amy/issues/1237
        """

        # Create a profile update for Ron but include Hermione's and Harry's
        # data. Only Ron doesn't have a GitHub nor Twitter accounts.
        pr1 = ProfileUpdateRequest.objects.create(
            active=True,
            personal='Ron', family='Weasley', airport_iata='AAA',
            gender='M', github='hpotter',
        )
        pr2 = ProfileUpdateRequest.objects.create(
            active=True,
            personal='Ron', family='Weasley', airport_iata='AAA',
            gender='M', twitter='herself',
        )
        pr3 = ProfileUpdateRequest.objects.create(
            active=True,
            personal='Ron', family='Weasley', airport_iata='AAA',
            gender='M', email='ron@weasley.com',
        )

        # ensure no new person was created so far
        self.assertEqual(
            Person.objects.filter(username__startswith='weasley_ron').count(),
            1
        )

        # now try to accept the profile updates for Ron Weasley
        rv1 = self.client.get(reverse('profileupdaterequest_accept',
                                      args=[pr1.pk, self.ron.pk]))
        self.assertEqual(rv1.status_code, 302)
        rv2 = self.client.get(reverse('profileupdaterequest_accept',
                                      args=[pr2.pk, self.ron.pk]))
        self.assertEqual(rv2.status_code, 302)

        # force create a new person from profile update, ensure no fail
        rv3 = self.client.get(reverse('profileupdaterequest_accept',
                                      args=[pr3.pk]))
        self.assertEqual(rv3.status_code, 302)

        # no update to github or twitter handles
        self.ron.refresh_from_db()
        self.assertEqual(self.ron.github, None)
        self.assertEqual(self.ron.twitter, None)

        # update requests are still active
        pr1.refresh_from_db()
        pr2.refresh_from_db()
        pr3.refresh_from_db()
        self.assertEqual(pr1.active, True)
        self.assertEqual(pr2.active, True)
        self.assertEqual(pr3.active, False)

        # make sure pr3 made a new person
        self.assertEqual(
            Person.objects.filter(username__startswith='weasley_ron').count(),
            2
        )


class TestUpdateRequestWithLowercasedAirport(TestBase):
    """Regression tests for [#1109] bug -- airport IATA code should be case
    insensitive.

    [#1109]: https://github.com/swcarpentry/amy/issues/1109"""

    def setUp(self):
        self._setUpAirports()
        self._setUpLessons()
        self._setUpBadges()
        self._setUpInstructors()
        self._setUpUsersAndLogin()

        self.request = ProfileUpdateRequest.objects.create(
            personal='Harry', family='Potter', email='harry@potter.com',
            airport_iata='aaa', affiliation='Hogwarts', active=True,
        )

    def test_the_airport_is_matched_when_displaying_the_request(self):
        rv = self.client.get(reverse('profileupdaterequest_details',
                                     args=[self.request.pk]))
        self.assertEqual(rv.context['airport'],
                         Airport.objects.get(iata='AAA'))

    def test_the_aiport_is_matched_when_accepting_the_request(self):
        expected_airport = Airport.objects.get(iata='AAA')

        person = Person.objects.get(personal='Harry', family='Potter')
        self.assertNotEqual(person.airport, expected_airport)

        self.client.get(reverse('profileupdaterequest_accept',
                                args=[self.request.pk, person.pk]))
        person.refresh_from_db()
        self.assertEqual(person.airport, expected_airport)


@patch('workshops.github_auth.github_username_to_uid', lambda username: None)
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
