from django.core.urlresolvers import reverse
from base import TestBase


class TestLocateInstructors(TestBase):
    '''Test cases for locating instructors.'''

    def test_search_for_instructors_by_airport(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : str(self.airport_0_0),
                                     'wanted' : 1})
        doc = self._check_status_code_and_parse(response, 200)
        row = self._get_1(doc, ".//tr[@class='instructor_row']",
                          'Expected a single matching instructor')
        personal = self._get_1(row, ".//td[@id='instructor_personal_0']",
                               'Expected a first name')
        family = self._get_1(row,  ".//td[@id='instructor_family_0']",
                             'Expected a last name')
        assert (personal.text == 'Hermione') and (family.text == 'Granger'), \
            'Expected matching instructor to be Hermione Granger'
