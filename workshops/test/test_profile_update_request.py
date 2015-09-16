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
            orcid='', website='http://warry.trotter.com/', gender='M',
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
        assert set(person.domains.all()) == \
            set(KnowledgeDomain.objects.all()[0:2])
        assert set(person.lessons.all()) == set(Lesson.objects.all()[0:2])
