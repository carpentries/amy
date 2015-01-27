from django.core.urlresolvers import reverse
from ..models import Person
from .base import TestBase


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

    def test_edit_person_email_when_all_fields_set(self):
        self._test_edit_person_email(self.ron)

    def test_edit_person_email_when_airport_not_set(self):
        self._test_edit_person_email(self.spiderman)

    def test_edit_person_empty_family_name(self):
        url, values = self._get_initial_form('person_edit', self.ironman.id)
        assert 'family' in values, \
            'No family name in initial form'

        values['family'] = '' # family name cannot be empty
        response = self.client.post(url, values)
        assert response.status_code == 200, \
            'Expected error page with status 200, got status {0}'.format(response.status_code)
        doc = self._parse(response=response)
        errors = self._collect_errors(doc)
        assert errors, \
            'Expected error messages in response page'

    def _test_edit_person_email(self, person):
        url, values = self._get_initial_form('person_edit', person.id)
        assert 'email' in values, \
            'No email address in initial form'

        new_email = 'new@new.new'
        assert person.email != new_email, \
            'Would be unable to tell if email had changed'
        values['email'] = new_email

        # Django redirects when edit works.
        response = self.client.post(url, values)
        if response.status_code == 302:
            new_person = Person.objects.get(id=person.id)
            assert new_person.email == new_email, \
                'Incorrect edited email: got {0}, expected {1}'.format(new_person.email, new_email)

        # Report errors.
        else:
            self._check_status_code_and_parse(response, 200)
            assert False, 'expected 302 redirect after post'

    def _check_person(self, doc, person):
        '''Check fields of person against document.'''
        fields = (('personal', person.personal),
                  ('family', person.family),
                  ('email', person.email),
                  ('gender', person.get_gender_display()),
                  ('may_contact', person.may_contact),
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
