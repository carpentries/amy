from django.core.urlresolvers import reverse
from ..models import Site, Person
from .base import TestBase


class TestSearchSite(TestBase):
    '''Test cases for searching on Site.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_search_for_site_with_no_matches(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'non.existent',
                                     'in_sites' : 'on'})
        doc = self._check_status_code_and_parse(response, 200)
        self._check_0(doc, ".//a[@class='searchresult']",
                      'Expected no search results')

    def test_search_for_site_when_site_matching_turned_off(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'Alpha'})
        doc = self._check_status_code_and_parse(response, 200)
        node = self._check_0(doc, ".//a[@class='searchresult']",
                             'Expected no search results')

    def test_search_for_site_by_partial_name(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'Alpha',
                                     'in_sites' : 'on'})
        doc = self._check_status_code_and_parse(response, 200)
        node = self._get_1(doc, ".//a[@class='searchresult']",
                           'Expected exactly one search result')
        assert node.text=='alpha.edu', \
            'Wrong name "{0}" in search result'.format(node.text)

    def test_search_for_site_by_full_domain(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'beta.com',
                                     'in_sites' : 'on'})
        doc = self._check_status_code_and_parse(response, 200)
        node = self._get_1(doc, ".//a[@class='searchresult']",
                           'Expected exactly one search result')
        assert node.text=='beta.com', \
            'Wrong name "{0}" in search result'.format(node.text)

    def test_search_for_site_with_multiple_matches(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'a', # 'a' is in both 'alpha' and 'beta'
                                     'in_sites' : 'on'})
        doc = self._check_status_code_and_parse(response, 200)
        nodes = self._get_N(doc,  ".//a[@class='searchresult']",
                            'Expected two search results',
                            expected=2)
        texts = set([n.text for n in nodes])
        assert texts == {'alpha.edu', 'beta.com'}, \
            'Wrong names {0} in search result'.format(texts)

    def test_search_for_people_by_personal_family_names(self):
        """Test if searching for two words yields people correctly."""
        # let's add Hermione Granger to some site's notes
        # this is required because of redirection if only 1 person matches
        self.site_alpha.notes = 'Hermione Granger'
        self.site_alpha.save()

        response = self.client.post(reverse('search'), {
            'term': 'Hermione Granger',
            'in_sites': 'on',
            'in_persons': 'on',
        })
        doc = self._check_status_code_and_parse(response, 200)
        nodes = self._get_N(doc, ".//a[@class='searchresult']",
                            'Expected two search results',
                            expected=2)
        texts = set([n.text for n in nodes])
        assert texts == {str(self.site_alpha), str(self.hermione)}, \
            'Wrong names {0} in search result'.format(texts)
