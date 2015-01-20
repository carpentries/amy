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
        # Get initial form.
        url = reverse('person_edit', args=[str(self.spiderman.id)])
        response = self.client.get(url)
        doc = self._check_status_code_and_parse(response, 200)
        values = self._get_form_data(doc)

        # Modify.
        assert 'email' in values, \
            'No email address in initial form'
        new_email = 'new@new.new'
        assert self.spiderman.email != new_email, \
            'Would be unable to tell if email had changed'
        values['email'] = new_email

        # Post and check.
        response = self.client.post(url, values)
        doc = self._check_status_code_and_parse(response, 200)
        import sys
        print >> sys.stderr, response.content
        family = self._get_field(doc, 'family name')
        assert family.text == 'Parker', \
            'Family name altered from "Parker" to {0} by changing email address'.format(family.text)
        email = self._get_field(doc, 'email')
        assert email.text == new_email, \
            'Incorrect edited email: expected {0}, got {1}'.format(new_email, email.text)

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
