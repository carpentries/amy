from django.core.urlresolvers import reverse
from ..models import Organization, Person, TrainingRequest
from .base import TestBase


class TestSearchOrganization(TestBase):
    '''Test cases for searching on Organization.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_search_for_organization_with_no_matches(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'non.existent',
                                     'in_organizations' : 'on'})
        doc = self._check_status_code_and_parse(response, 200)
        self._check_0(doc, ".//a[@class='searchresult']",
                      'Expected no search results')

    def test_search_for_organization_when_host_matching_turned_off(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'Alpha'})
        doc = self._check_status_code_and_parse(response, 200)
        node = self._check_0(doc, ".//a[@class='searchresult']",
                             'Expected no search results')

    def test_search_for_organization_by_partial_name(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'Alpha',
                                     'in_organizations' : 'on'},
                                    follow=True)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # no way for us to check the url…
        assert str(self.org_alpha.domain) in content

    def test_search_for_organization_by_full_domain(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'beta.com',
                                     'in_organizations' : 'on'},
                                    follow=True)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # no way for us to check the url…
        assert str(self.org_beta.domain) in content

    def test_search_for_organization_with_multiple_matches(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'a', # 'a' is in both 'alpha' and 'beta'
                                     'in_organizations' : 'on'})
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

        response = self.client.post(reverse('search'), {
            'term': 'Hermione Granger',
            'in_organizations': 'on',
            'in_persons': 'on',
        })
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

        search_options = {
            'term': 'Leprechaun',
            'in_training_requests': 'on',
            'in_persons': 'on',
        }
        url = reverse('search')

        response = self.client.post(url, search_options)
        self.assertEqual(len(response.context['training_requests']), 1)

        search_options['term'] = 'Krum'
        response = self.client.post(url, search_options)
        self.assertEqual(len(response.context['training_requests']), 1)

        search_options['term'] = 'Lorem'
        response = self.client.post(url, search_options)
        self.assertEqual(len(response.context['training_requests']), 1)

        search_options['term'] = 'Potter'
        # otherwise it'd redirect to Harry Potter's profile
        del search_options['in_persons']
        response = self.client.post(url, search_options)
        self.assertEqual(len(response.context['training_requests']), 0)

