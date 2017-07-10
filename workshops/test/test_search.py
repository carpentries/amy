from django.core.urlresolvers import reverse
from ..models import Organization, Person, TrainingRequest
from .base import TestBase


class TestSearchOrganization(TestBase):
    '''Test cases for searching on Organization.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def search_for(self, term,
                   in_organizations=False,
                   in_training_requests=False,
                   in_persons=False):
        search_page = self.app.get(reverse('search'), user='admin')
        form = search_page.forms['main-form']
        form['term'] = term
        form['in_organizations'] = in_organizations
        form['in_training_requests'] = in_training_requests
        form['in_persons'] = in_persons
        return form.submit().maybe_follow()

    def test_search_for_organization_with_no_matches(self):
        response = self.search_for('non.existent', in_organizations=True)
        doc = self._check_status_code_and_parse(response, 200)
        self._check_0(doc, ".//a[@class='searchresult']",
                      'Expected no search results')

    def test_search_for_organization_when_host_matching_turned_off(self):
        response = self.search_for('Alpha')
        doc = self._check_status_code_and_parse(response, 200)
        node = self._check_0(doc, ".//a[@class='searchresult']",
                             'Expected no search results')

    def test_search_for_organization_by_partial_name(self):
        response = self.search_for('Alpha', in_organizations=True)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # no way for us to check the url…
        assert str(self.org_alpha.domain) in content

    def test_search_ignores_case(self):
        response = self.search_for('AlPhA', in_organizations=True)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # no way for us to check the url…
        assert str(self.org_alpha.domain) in content

    def test_search_for_organization_by_full_domain(self):
        response = self.search_for('beta.com', in_organizations=True)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # no way for us to check the url…
        assert str(self.org_beta.domain) in content

    def test_search_for_organization_with_multiple_matches(self):
        # 'a' is in both 'alpha' and 'beta'
        response = self.search_for('a', in_organizations=True)
        doc = self._check_status_code_and_parse(response, 200)
        nodes = self._get_N(doc,  ".//a[@class='searchresult']",
                            'Expected three search results',
                            expected=3)
        texts = set([n.text for n in nodes])
        assert texts == {'alpha.edu', 'self-organized', 'beta.com'}, \
            'Wrong names {0} in search result'.format(texts)

    def test_search_for_people_by_personal_family_names(self):
        """Test if searching for two words yields people correctly."""
        # let's add Hermione Granger to some organization's notes
        # this is required because of redirection if only 1 person matches
        self.org_alpha.notes = 'Hermione Granger'
        self.org_alpha.save()

        response = self.search_for(
            'Hermione Granger', in_organizations=True, in_persons=True)
        doc = self._check_status_code_and_parse(response, 200)
        nodes = self._get_N(doc, ".//a[@class='searchresult']",
                            'Expected two search results',
                            expected=2)
        texts = set([n.text for n in nodes])
        assert texts == {str(self.org_alpha.domain), str(self.hermione)}, \
            'Wrong names {0} in search result'.format(texts)

    def test_search_for_training_requests(self):
        """Make sure that finding training requests works."""

        # added so that the search doesn't redirect with only 1 result
        Person.objects.create(
            personal='Victor', family='Krum', email='vkrum@durmstrang.edu',
            github='vkrum Lorem Ipsum Leprechauns',
        )

        TrainingRequest.objects.create(
            group_name='Leprechauns', personal='Victor', family='Krum',
            email='vkrum@durmstrang.edu', github='vkrum',
            comment='Lorem Ipsum',
        )

        response = self.search_for(
            'Leprechaun', in_training_requests=True, in_persons=True)
        self.assertEqual(len(response.context['training_requests']), 1)

        response = self.search_for(
            'Krum', in_training_requests=True, in_persons=True)
        self.assertEqual(len(response.context['training_requests']), 1)

        response = self.search_for(
            'Lorem', in_training_requests=True, in_persons=True)
        self.assertEqual(len(response.context['training_requests']), 1)

        # do not search in_persons, otherwise it'd redirect to Harry Potter's profile
        response = self.search_for('Potter', in_training_requests=True)
        self.assertEqual(len(response.context['training_requests']), 0)
