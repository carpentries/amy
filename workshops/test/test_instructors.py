from django.core.urlresolvers import reverse
from .base import TestBase


class TestLocateInstructors(TestBase):
    '''Test cases for locating instructors.'''

    def test_search_for_one_instructor_by_airport(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_0_0.iata,
                                     'wanted' : 1})
        doc = self._check_status_code_and_parse(response, 200)
        row = self._get_1(doc, ".//tr[@class='instructor_row']",
                          'Expected a single matching instructor')
        self._check_person(row, 0, 'Hermione', 'Granger')

    def test_search_for_two_instructors_by_airport(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_0_0.iata,
                                     'wanted' : 2})
        doc = self._check_status_code_and_parse(response, 200)
        rows = self._get_N(doc, ".//tr[@class='instructor_row']",
                           'Expected 2 matching instructors',
                           expected=2)
        self._check_person(rows[0], 0, 'Hermione', 'Granger')
        self._check_person(rows[1], 1, 'Harry', 'Potter')

    def test_search_for_one_instructor_near_airport(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_55_105.iata,
                                     'wanted' : 1})
        doc = self._check_status_code_and_parse(response, 200)
        row = self._get_1(doc, ".//tr[@class='instructor_row']",
                          'Expected a single matching instructor')
        self._check_person(row, 0, 'Ron', 'Weasley')

    def test_search_for_one_instructor_near_latlong(self):
        response = self.client.post(reverse('instructors'),
                                    {'latitude' : 5,
                                     'longitude' : 45,
                                     'wanted' : 1})
        doc = self._check_status_code_and_parse(response, 200)
        row = self._get_1(doc, ".//tr[@class='instructor_row']",
                          'Expected a single matching instructor')
        self._check_person(row, 0, 'Harry', 'Potter')

    def test_non_instructors_not_returned_by_search(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_0_0.iata,
                                     'wanted' : 1000})
        doc = self._check_status_code_and_parse(response, 200)
        rows = self._get_N(doc, ".//tr[@class='instructor_row']",
                           'Expected 3 matching instructors',
                           expected=3)
        self._check_person(rows[0], 0, 'Hermione', 'Granger')
        self._check_person(rows[1], 1, 'Harry', 'Potter')
        self._check_person(rows[2], 2, 'Ron', 'Weasley')

    def test_match_instructors_on_one_skill(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_50_100.iata,
                                     'Git' : 'on',
                                     'wanted' : 1000})
        doc = self._check_status_code_and_parse(response, 200)
        rows = self._get_N(doc, ".//tr[@class='instructor_row']",
                           'Expected 2 matching instructors',
                           expected=2)
        self._check_person(rows[0], 0, 'Ron', 'Weasley')
        self._check_person(rows[1], 1, 'Hermione', 'Granger')

    def test_match_instructors_on_two_skills(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_50_100.iata,
                                     'Git' : 'on',
                                     'SQL' : 'on',
                                     'wanted' : 1000})
        doc = self._check_status_code_and_parse(response, 200)
        row = self._get_1(doc, ".//tr[@class='instructor_row']",
                          'Expected 1 matching instructor')
        self._check_person(row, 0, 'Hermione', 'Granger')

    def _check_person(self, row, which, personal_name, family_name):
        personal_node = self._get_1(row, ".//td[@id='instructor_personal_{0}']".format(which),
                                    'Expected a first name')
        family_node = self._get_1(row,  ".//td[@id='instructor_family_{0}']".format(which),
                                  'Expected a last name')
        assert (personal_node.text == personal_name) and (family_node.text == family_name), \
            'Expected instructor to be Hermione Granger, not "{0} {1}"'.format(personal_node.text, family_node.text)
