import cgi
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
        
    def test_merge_duplicate_persons(self):
        assert self.spiderman.airport == None
        assert self.benreilly.github == 'benreilly'
        url, values = self._get_initial_form('person_find_duplicates')
        assert len(values)>0
        values['4'] = 'on'
        values['5'] = 'on'
        response = self.client.post(url, values)
        doc = self._check_status_code_and_parse(response, 200)
        values = self._get_form_data(doc)
        assert 'Confirm' in values
        values['Peter_Parker_primary'] = '4'
        response = self.client.post(url, values, follow=True) # Confirm, following redirect
        _, params = cgi.parse_header(response['content-type'])
        charset = params['charset']
        content = response.content.decode(charset)
        assert 'Merge success' in content
        spiderman = Person.objects.get(username="spiderman")
        assert spiderman.github == 'benreilly' # Check benreilly's github was merged in
        
    def test_merge_fails_when_fields_not_set(self):
        url, values = self._get_initial_form('person_find_duplicates')
        assert len(values)>0
        response = self.client.post(url, {'Merge':'yes'}, follow=True)
        _, params = cgi.parse_header(response['content-type'])
        charset = params['charset']
        content = response.content.decode(charset)
        assert 'You must select at least two duplicate entries' in content
        
    def test_merge_fails_when_github_mismatch(self):
        self.spiderman.github = 'spiderman'
        self.spiderman.save()
        url, values = self._get_initial_form('person_find_duplicates')
        assert len(values)>0
        values['4'] = 'on'
        values['5'] = 'on'
        response = self.client.post(url, values, follow=True)
        _, params = cgi.parse_header(response['content-type'])
        charset = params['charset']
        content = response.content.decode(charset)
        assert 'mismatched github' in content

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
            else:
                assert node.text == str(value), \
                    'Mis-match in {0}: expected {1}/{2}, got {3}' \
                    .format(key, value, type(value), node.text)

    def _get_field(self, doc, key):
        '''Get field from person display.'''
        xpath = ".//td[@id='{0}']".format(key)
        return self._get_1(doc, xpath, key)
