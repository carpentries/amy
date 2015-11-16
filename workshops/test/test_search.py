from django.core.urlresolvers import reverse
from ..models import Host, Person
from .base import TestBase


class TestSearchHost(TestBase):
    '''Test cases for searching on Host.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_search_for_host_with_no_matches(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'non.existent',
                                     'in_hosts' : 'on'})
        doc = self._check_status_code_and_parse(response, 200)
        self._check_0(doc, ".//a[@class='searchresult']",
                      'Expected no search results')

    def test_search_for_host_when_host_matching_turned_off(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'Alpha'})
        doc = self._check_status_code_and_parse(response, 200)
        node = self._check_0(doc, ".//a[@class='searchresult']",
                             'Expected no search results')

    def test_search_for_host_by_partial_name(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'Alpha',
                                     'in_hosts' : 'on'},
                                    follow=True)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # no way for us to check the url…
        assert str(self.host_alpha) in content

    def test_search_for_host_by_full_domain(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'beta.com',
                                     'in_hosts' : 'on'},
                                    follow=True)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # no way for us to check the url…
        assert str(self.host_beta) in content

    def test_search_for_host_with_multiple_matches(self):
        response = self.client.post(reverse('search'),
                                    {'term' : 'a', # 'a' is in both 'alpha' and 'beta'
                                     'in_hosts' : 'on'})
        doc = self._check_status_code_and_parse(response, 200)
        nodes = self._get_N(doc,  ".//a[@class='searchresult']",
                            'Expected three search results',
                            expected=3)
        texts = set([n.text for n in nodes])
        assert texts == {'alpha.edu', 'self-organized', 'beta.com'}, \
            'Wrong names {0} in search result'.format(texts)

    def test_search_for_people_by_personal_family_names(self):
        """Test if searching for two words yields people correctly."""
        # let's add Hermione Granger to some host's notes
        # this is required because of redirection if only 1 person matches
        self.host_alpha.notes = 'Hermione Granger'
        self.host_alpha.save()

        response = self.client.post(reverse('search'), {
            'term': 'Hermione Granger',
            'in_hosts': 'on',
            'in_persons': 'on',
        })
        doc = self._check_status_code_and_parse(response, 200)
        nodes = self._get_N(doc, ".//a[@class='searchresult']",
                            'Expected two search results',
                            expected=2)
        texts = set([n.text for n in nodes])
        assert texts == {str(self.host_alpha), str(self.hermione)}, \
            'Wrong names {0} in search result'.format(texts)
