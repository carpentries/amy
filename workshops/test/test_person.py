# coding: utf-8

from django.core.urlresolvers import reverse
from ..models import Person
from .base import TestBase


class TestPerson(TestBase):
    '''Test cases for persons.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

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

        if values['airport_1'] is None:
            values['airport_1'] = ''
        if values['airport_0'] is None:
            values['airport_0'] = ''

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
                  ('may_contact', 'yes' if person.may_contact else 'no'),
                  ('airport', person.airport),
                  ('github', person.github),
                  ('twitter', person.twitter),
                  ('url', person.url))
        for (key, value) in fields:
            node = self._get_field(doc, key)

            if isinstance(value, bool):
                # bool is a special case because we can show it as either
                # "True" or "yes" (alternatively "False" or "no")
                assert node.text in (str(value), "yes" if value else "no"), \
                    'Mis-match in {0}: expected boolean value, got {1}' \
                    .format(key, node.text)
            elif value is None:
                # None is also a special case.  We should handle:
                # "None", "unknown", "maybe", or even "—" (mdash)
                assert node.text in (str(value), "unknown", "maybe", "—"), \
                    'Mis-match in {0}: expected boolean value, got {1}' \
                    .format(key, node.text)
            else:
                if node.text is None:
                    # emails, URLs and some FKs are usually urlized, so we need
                    # to go deeper: to the first child of current node
                    node = node[0]
                assert node.text == str(value), \
                    'Mis-match in {0}: expected {1}/{2}, got {3}' \
                    .format(key, value, type(value), node.text)

    def _get_field(self, doc, key):
        '''Get field from person display.'''
        xpath = ".//td[@id='{0}']".format(key)
        return self._get_1(doc, xpath, key)

    def test_display_person_without_notes(self):
        response = self.client.get(reverse('person_details',
                                           args=[str(self.ironman.id)]))
        assert response.status_code == 200

        content = response.content.decode('utf-8')
        assert "No notes" in content

    def test_display_person_with_notes(self):
        note = 'This person has some serious records'
        p = Person.objects.create(personal='P1', family='P1',
                                  email='p1@p1.net',
                                  notes=note)

        response = self.client.get(reverse('person_details',
                                           args=[str(p.id)]))

        assert response.status_code == 200

        content = response.content.decode('utf-8')
        assert "No notes" not in content
        assert note in content

    def test_edit_person_notes(self):
        url, values = self._get_initial_form('person_edit', self.hermione.id)

        assert 'notes' in values, 'Notes not present in initial form'

        note = 'Hermione is a very good student.'
        values['notes'] = note

        # Django redirects when edit works.
        response = self.client.post(url, values)
        if response.status_code == 302:
            new_person = Person.objects.get(id=self.hermione.id)
            assert new_person.notes == note, \
                'Incorrect edited notes: got {0}, expected {1}'.format(new_person.notes, note)

        # Report errors.
        else:
            self._check_status_code_and_parse(response, 200)
            assert False, 'expected 302 redirect after post'
