from django.core.urlresolvers import reverse
from ..models import Person
from base import TestBase


class TestPerson(TestBase):
    '''Test cases for persons.'''

    def test_display_person_correctly_with_all_fields(self):
        response = self.client.get(reverse('person_details', args=[str(self.hermione.id)]))
        doc = self._check_status_code_and_parse(response, 200)
        self._check_person(doc, self.hermione)

    def test_display_person_correctly_with_some_fields(self):
        response = self.client.get(reverse('person_details', args=[str(self.ironman.id)]))
        doc = self._check_status_code_and_parse(response, 200)
        self._check_person(doc, self.ironman)

    def test_edit_person_email(self):
        new_email = 'new@new.new'
        assert self.spiderman.email != new_email, \
            'Would be unable to tell if email had changed'
        response = self.client.post(reverse('person_edit', args=[str(self.spiderman.id)]),
                                    {'email' : new_email})
        doc = self._check_status_code_and_parse(response, 200)
        node = self._get_field(doc, 'email')
        assert node.text == new_email, \
            'Incorrect edited email: expected {0}, got {1}'.format(new_email, node.text)

    def _check_person(self, doc, person):
        '''Check fields of person against document.'''
        fields = (('personal', person.personal),
                  ('family', person.family),
                  ('email', person.email),
                  ('gender', Person.GENDER_CHOICES_DICT.get(person.gender, None)),
                  ('active', person.active),
                  ('airport', person.airport),
                  ('github', person.github),
                  ('twitter', person.twitter),
                  ('url', person.url))
        for (key, value) in fields:
            node = self._get_field(doc, key)
            assert node.text == str(value), \
                'Mis-match in {0}: expected {1}/{2}, got {3}'.format(key, value, type(value), node.text)

    def _get_field(self, doc, key):
        '''Get field from person display.'''
        xpath = ".//td[@id='{0}']".format(key)
        return self._get_1(doc, xpath, key)
