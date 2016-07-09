# coding: utf-8

import datetime
from social.apps.django_app.default.models import UserSocialAuth
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import authenticate
from django.core.urlresolvers import reverse
from django.core.validators import ValidationError
from django.contrib.auth.models import Permission, Group

from ..forms import PersonForm, PersonCreateForm, PersonsMergeForm
from ..models import (
    Person, Task, Qualification, Award, Role, Event, KnowledgeDomain, Badge,
    Lesson, Organization, Language,
)
from .base import TestBase


@patch('workshops.github_auth.github_username_to_uid', lambda username: None)
class TestPerson(TestBase):
    '''Test cases for persons.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_login_with_email(self):
        """Make sure we can login with user's email too, not only with the
        username."""
        self.client.logout()
        email = 'sudo@example.org'  # admin's email
        user = authenticate(username=email, password='admin')
        self.assertEqual(user, self.admin)

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
        data = {
            'person-family': '',  # family name cannot be empty
        }
        f = PersonForm(data)
        self.assertIn('family', f.errors)

    def _test_edit_person_email(self, person):
        url, values = self._get_initial_form_index(0, 'person_edit', person.id)
        assert 'person-email' in values, \
            'No email address in initial form'

        new_email = 'new@new.new'
        assert person.email != new_email, \
            'Would be unable to tell if email had changed'
        values['person-email'] = new_email

        if values['person-airport_1'] is None:
            values['person-airport_1'] = ''
        if values['person-airport_0'] is None:
            values['person-airport_0'] = ''

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
            elif not value:
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
        url, values = self._get_initial_form_index(0, 'person_edit',
                                                   self.hermione.id)

        assert 'person-notes' in values, 'Notes not present in initial form'

        note = 'Hermione is a very good student.'
        values['person-notes'] = note

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

    def test_person_award_badge(self):
        # make sure person has no awards
        assert not self.spiderman.award_set.all()

        # add new award
        url, values = self._get_initial_form_index(1, 'person_edit',
                                                   self.spiderman.id)
        assert 'award-badge' in values

        values['award-badge'] = self.swc_instructor.pk
        values['award-event_1'] = ''
        values['award-awarded_by_0'] = ''
        values['award-awarded_by_1'] = ''

        rv = self.client.post(url, data=values)
        assert rv.status_code == 302, \
            'After awarding a badge we should be redirected to the same page, got {} instead'.format(rv.status_code)
        # we actually can't test if it redirects to the same url…

        # make sure the award was recorded in the database
        self.spiderman.refresh_from_db()
        assert self.swc_instructor == self.spiderman.award_set.all()[0].badge

    def test_person_add_task(self):
        self._setUpEvents()  # set up some events for us

        # make sure person has no tasks
        assert not self.spiderman.task_set.all()

        # add new task
        url, values = self._get_initial_form_index(2, 'person_edit',
                                                   self.spiderman.id)
        assert 'task-role' in values

        role = Role.objects.create(name='test_role')
        values['task-event_1'] = Event.objects.all()[0].pk
        values['task-role'] = role.pk
        rv = self.client.post(url, data=values)
        assert rv.status_code == 302, \
            'After adding a task we should be redirected to the same page, ' \
            'got {} instead'.format(rv.status_code)
        # we actually can't test if it redirects to the same url…

        # make sure the task was recorded in the database
        self.spiderman.refresh_from_db()
        assert role == self.spiderman.task_set.all()[0].role

    def test_edit_person_permissions(self):
        "Make sure we can set up user permissions correctly."

        # make sure Hermione does not have any perms, nor groups
        assert not self.hermione.is_superuser
        assert self.hermione.user_permissions.count() == 0
        assert self.hermione.groups.count() == 0

        user_permissions = Permission.objects \
            .filter(content_type__app_label='admin')
        user_permissions_ids = user_permissions.values_list('id', flat=True) \
            .order_by('id')

        groups = Group.objects.all()
        groups_ids = groups.values_list('id', flat=True).order_by('id')

        data = {
            'is_superuser': True,
            'user_permissions': user_permissions_ids,
            'groups': groups_ids,
        }

        response = self.client.post(
            reverse('person_permissions', args=[self.hermione.id]),
            data,
        )

        assert response.status_code == 302

        self.hermione.refresh_from_db()
        assert self.hermione.is_superuser
        assert \
            set(self.hermione.user_permissions.all()) == set(user_permissions)
        assert set(self.hermione.groups.all()) == set(groups)

    def test_delete_person(self):
        """Make sure deleted person is longer accessible.

        Additionally check on_delete behavior for Task, Qualification, and
        Award."""
        role = Role.objects.create(name='instructor')
        event = Event.objects.create(slug='test-event', host=self.org_alpha)
        people = [self.hermione, self.harry, self.ron]

        for person in people:
            # folks don't have any tasks by default, so let's add one
            person.task_set.create(event=event, role=role)

            awards = person.award_set.all()
            qualifications = person.qualification_set.all()
            tasks = person.task_set.all()

            rv = self.client.get(reverse('person_delete', args=[person.pk, ]))
            assert rv.status_code == 302

            with self.assertRaises(Person.DoesNotExist):
                Person.objects.get(pk=person.pk)

            for award in awards:
                with self.assertRaises(Award.DoesNotExist):
                    Award.objects.get(pk=award.pk)
            for qualification in qualifications:
                with self.assertRaises(Qualification.DoesNotExist):
                    Qualification.objects.get(pk=qualification.pk)
            for task in tasks:
                with self.assertRaises(Task.DoesNotExist):
                    Task.objects.get(pk=task.pk)

    def test_editing_qualifications(self):
        """Make sure we can edit user lessons without any issues."""
        assert set(self.hermione.lessons.all()) == set([self.git, self.sql])

        url, values = self._get_initial_form_index(0, 'person_edit',
                                                   self.hermione.id)
        values['person-lessons'] = [self.git.pk]

        response = self.client.post(url, values)
        assert response.status_code == 302
        assert set(self.hermione.lessons.all()) == set([self.git, ])

    def test_person_add_lessons(self):
        "Check if it's still possible to add lessons via PersonCreate view."
        data = {
            'username': 'test',
            'personal': 'Test',
            'family': 'Test',
            'gender': 'U',
            'lessons': [1, 2],  # just IDs
        }
        rv = self.client.post(reverse('person_add'), data)
        assert rv.status_code == 302

        # make sure "no lessons" works too
        data = {
            'username': 'test2',
            'personal': 'Test',
            'family': 'Test',
            'gender': 'U',
            'lessons': [],
        }
        rv = self.client.post(reverse('person_add'), data)
        assert rv.status_code == 302

    def test_person_success_message(self):
        """Since PersonCreate view simulates SuccessMessageMixin, check if it
        does it correctly."""
        data = {
            'username': 'test',
            'personal': 'Test',
            'family': 'Test',
            'gender': 'U',
            'lessons': [1, 2],  # just IDs
        }
        rv = self.client.post(reverse('person_add'), data, follow=True)
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert "Test Test was created successfully." in content

    def test_person_username_validation(self):
        """Ensure username doesn't allow for non-ASCII characters."""
        invalid_usernames = ['Zażółć gęślą jaźń', 'chrząszcz']
        for username in invalid_usernames:
            with self.subTest(username=username):
                person = Person.objects.create(
                    personal='Testing', family='Testing', username=username,
                )
                with self.assertRaises(ValidationError) as cm:
                    person.clean_fields(exclude=['password'])
                self.assertIn('username', cm.exception.message_dict)

        valid_username = 'blanking-crush_andy'
        person = Person.objects.create(
            personal='Andy', family='Blanking-Crush', username=valid_username,
        )
        person.clean_fields(exclude=['password'])

    def test_new_person_auto_username(self):
        """Ensure after adding a new person, they're automatically assigned
        a unique username."""
        url = reverse('person_add')
        data = {
            'personal': 'Albert',
            'family': 'Einstein',
            'gender': 'U',
        }
        self.client.post(url, data)
        Person.objects.get(personal='Albert', family='Einstein',
                           username='einstein_albert')

    def test_person_email_auto_lowercase(self):
        """Make sure PersonForm/PersonCreateForm lowercases user's email."""
        data = {
            'username': 'curie_marie',
            'personal': 'Marie',
            'family': 'Curie',
            'gender': 'F',
            'email': 'M.CURIE@sorbonne.fr',
        }
        url = reverse('person_add')
        self.client.post(url, data)
        person = Person.objects.get(username='curie_marie')
        self.assertEqual(person.email, 'm.curie@sorbonne.fr')

        url = reverse('person_edit', args=[person.pk])
        self.client.post(url, data)
        person.refresh_from_db()
        self.assertEqual(person.email, 'm.curie@sorbonne.fr')

    def test_edit_permission_of_person_without_email(self):
        """
        Creating a person without email id and then changing
        the permissions for that person.
        """
        p = Person.objects.create(personal='P1', family='P1')
        response = self.client.get(reverse('person_details',
                                           args=[str(p.id)]))
        assert response.status_code == 200

        user_permissions = Permission.objects \
            .filter(content_type__app_label='admin')
        user_permissions_ids = user_permissions.values_list('id', flat=True) \
            .order_by('id')

        groups = Group.objects.all()
        groups_ids = groups.values_list('id', flat=True).order_by('id')

        data = {
            'is_superuser': True,
            'user_permissions': user_permissions_ids,
            'groups': groups_ids,
        }

        response = self.client.post(
            reverse('person_permissions', args=[str(p.id)]),
            data,
        )
        assert response.status_code == 302


class TestPersonPassword(TestBase):
    """Separate tests for testing password setting.

    They need to be in separate class that doesn't call
    self._setUpUsersAndLogin().
    """

    def setUp(self):
        admins, _ = Group.objects.get_or_create(name='administrators')

        # create a superuser
        self.admin = Person.objects.create_superuser(
            username='admin', personal='Super', family='User',
            email='sudo@example.org', password='admin',
        )

        # create a normal user
        self.user = Person.objects.create_user(
            username='user', personal='Typical', family='User',
            email='undo@example.org', password='user',
        )
        self.user.groups.add(admins)

    def test_edit_password_by_superuser(self):
        self.client.login(username='admin', password='admin')
        user = self.admin
        url, form = self._get_initial_form('person_password', user.pk)

        # check that correct form is rendered
        assert 'old_password' not in form
        assert 'new_password1' in form
        assert 'new_password2' in form

        # try incorrect form data first
        new_password = 'new_password'
        data = {
            'new_password1': new_password,
            'new_password2': 'asdf',
        }
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        # update password
        data['new_password2'] = new_password
        rv = self.client.post(url, data)
        assert rv.status_code == 302

        # make sure password was updated
        user.refresh_from_db()
        assert user.check_password(new_password) is True

    def test_edit_other_user_password_by_superuser(self):
        self.client.login(username='admin', password='admin')
        user = self.user
        url, form = self._get_initial_form('person_password', user.pk)

        # check that correct form is rendered
        assert 'old_password' not in form
        assert 'new_password1' in form
        assert 'new_password2' in form

        # try incorrect form data first
        new_password = 'new_password'
        data = {
            'new_password1': new_password,
            'new_password2': 'asdf',
        }
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        # update password
        data['new_password2'] = new_password
        rv = self.client.post(url, data)
        assert rv.status_code == 302

        # make sure password was updated
        user.refresh_from_db()
        assert user.check_password(new_password) is True

    def test_edit_password_by_normal_user(self):
        self.client.login(username='user', password='user')
        user = self.user
        url, form = self._get_initial_form('person_password', user.pk)

        # check that correct form is rendered
        assert 'old_password' in form
        assert 'new_password1' in form
        assert 'new_password2' in form

        # try incorrect form data first
        new_password = 'new_password'
        data = {
            'old_password': 'asdf',
            'new_password1': new_password,
            'new_password2': 'asdf',
        }
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        data['old_password'] = 'user'
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        # update password
        data['new_password2'] = new_password
        rv = self.client.post(url, data)
        assert rv.status_code == 302

        # make sure password was updated
        user.refresh_from_db()
        assert user.check_password(new_password) is True

    def test_edit_other_user_password_by_normal_user(self):
        self.client.login(username='user', password='user')
        user = self.admin
        rv = self.client.get(reverse('person_password', args=[user.pk]))
        assert rv.status_code == 403


class TestPersonMerging(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpBadges()
        self._setUpLessons()
        self._setUpRoles()
        self._setUpEvents()
        self._setUpUsersAndLogin()

        self.person_a = Person.objects.create(
            personal='Kelsi', middle='', family='Purdy',
            username='purdy_kelsi', email='purdy.kelsi@example.com',
            gender='F', may_contact=True, airport=self.airport_0_0,
            github='purdy_kelsi', twitter='purdy_kelsi',
            url='http://kelsipurdy.com/', notes='',
            affiliation='University of Arizona',
            occupation='TA at Biology Department', orcid='0000-0000-0000',
            is_active=True,
        )
        self.person_a.award_set.create(badge=self.swc_instructor,
                                       awarded=datetime.date(2016, 2, 16))
        Qualification.objects.create(person=self.person_a, lesson=self.git)
        Qualification.objects.create(person=self.person_a, lesson=self.sql)
        self.person_a.domains = [KnowledgeDomain.objects.first()]
        self.person_a.task_set.create(
            event=Event.objects.get(slug='ends-tomorrow-ongoing'),
            role=Role.objects.get(name='instructor'),
        )
        self.person_a.languages.set([Language.objects.first(),
                                     Language.objects.last()])

        self.person_b = Person.objects.create(
            personal='Jayden', middle='', family='Deckow',
            username='deckow_jayden', email='deckow.jayden@example.com',
            gender='M', may_contact=True, airport=self.airport_0_50,
            github='deckow_jayden', twitter='deckow_jayden',
            url='http://jaydendeckow.com/', notes='deckow_jayden',
            affiliation='UFlo',
            occupation='Staff', orcid='0000-0000-0001',
            is_active=True,
        )
        self.person_b.award_set.create(badge=self.dc_instructor,
                                       awarded=datetime.date(2016, 2, 16))
        Qualification.objects.create(person=self.person_b, lesson=self.sql)
        self.person_b.domains = [KnowledgeDomain.objects.last()]
        self.person_b.languages.set([Language.objects.last()])

        self.strategy = {
            'person_a': self.person_a.pk,
            'person_b': self.person_b.pk,
            'id': 'obj_b',
            'username': 'obj_a',
            'personal': 'obj_b',
            'middle': 'obj_a',
            'family': 'obj_a',
            'email': 'obj_b',
            'may_contact': 'obj_a',
            'gender': 'obj_b',
            'airport': 'obj_a',
            'github': 'obj_b',
            'twitter': 'obj_a',
            'url': 'obj_b',
            'notes': 'combine',
            'affiliation': 'obj_b',
            'occupation': 'obj_a',
            'orcid': 'obj_b',
            'award_set': 'obj_a',
            'qualification_set': 'obj_b',
            'domains': 'combine',
            'languages': 'combine',
            'task_set': 'obj_b',
            'is_active': 'obj_a',
        }
        base_url = reverse('persons_merge')
        query = urlencode({
            'person_a_1': self.person_a.pk,
            'person_b_1': self.person_b.pk
        })
        self.url = '{}?{}'.format(base_url, query)

    def test_form_invalid_values(self):
        """Make sure only a few fields accept third option ("combine")."""
        hidden = {
            'person_a': self.person_a.pk,
            'person_b': self.person_b.pk,
        }
        # fields accepting only 2 options: "obj_a" and "obj_b"
        failing = {
            'id': 'combine',
            'username': 'combine',
            'personal': 'combine',
            'middle': 'combine',
            'family': 'combine',
            'email': 'combine',
            'may_contact': 'combine',
            'gender': 'combine',
            'airport': 'combine',
            'github': 'combine',
            'twitter': 'combine',
            'url': 'combine',
            'affiliation': 'combine',
            'occupation': 'combine',
            'orcid': 'combine',
            'is_active': 'combine',
        }
        # fields additionally accepting "combine"
        passing = {
            'notes': 'combine',
            'award_set': 'combine',
            'qualification_set': 'combine',
            'domains': 'combine',
            'languages': 'combine',
            'task_set': 'combine',
        }
        data = hidden.copy()
        data.update(failing)
        data.update(passing)

        form = PersonsMergeForm(data)
        self.assertFalse(form.is_valid())

        for key in failing:
            self.assertIn(key, form.errors)
        for key in passing:
            self.assertNotIn(key, form.errors)

        # make sure no fields are added without this test being updated
        self.assertEqual(set(list(form.fields.keys())), set(list(data.keys())))

    def test_merging_base_person(self):
        """Merging: ensure the base person is selected based on ID form
        field.

        If ID field has a value of 'obj_a', then person A is base event and it
        won't be removed from the database after the merge. Person B, on the
        other hand, will."""
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)

        self.person_b.refresh_from_db()
        with self.assertRaises(Person.DoesNotExist):
            self.person_a.refresh_from_db()

    def test_merging_basic_attributes(self):
        """Merging: ensure basic (non-relationships) attributes are properly
        saved."""
        assertions = {
            'id': self.person_b.id,
            'username': self.person_a.username,
            'personal': self.person_b.personal,
            'middle': self.person_a.middle,
            'family': self.person_a.family,
            'email': self.person_b.email,
            'may_contact': self.person_a.may_contact,
            'gender': self.person_b.gender,
            'airport': self.person_a.airport,
            'github': self.person_b.github,
            'twitter': self.person_a.twitter,
            'url': self.person_b.url,
            'notes': self.person_a.notes + self.person_b.notes,
            'affiliation': self.person_b.affiliation,
            'occupation': self.person_a.occupation,
            'orcid': self.person_b.orcid,
            'is_active': self.person_a.is_active,
        }
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(getattr(self.person_b, key), value, key)

    def test_merging_relational_attributes(self):
        """Merging: ensure M2M-related fields are properly saved/combined."""
        assertions = {
            # instead testing awards, let's simply test badges
            'badges': set(Badge.objects.filter(name='swc-instructor')),
            # we're saving/combining qualifications, but it affects lessons
            'lessons': set([self.sql]),
            'domains': set([KnowledgeDomain.objects.first(),
                            KnowledgeDomain.objects.last()]),
            'languages': set([Language.objects.first(),
                              Language.objects.last()]),
            'task_set': set(Task.objects.none()),
        }

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(set(getattr(self.person_b, key).all()), value,
                             key)

    def test_merging_m2m_attributes(self):
        """Merging: ensure M2M-related fields are properly saved/combined.
        This is a regression test; we have to ensure that M2M objects aren't
        removed from the database."""
        assertions = {
            # instead testing awards, let's simply test badges
            'badges': set(Badge.objects.filter(name='swc-instructor')),
            # we're saving/combining qualifications, but it affects lessons
            'lessons': set([self.sql, self.git]),
            'domains': set([KnowledgeDomain.objects.first(),
                            KnowledgeDomain.objects.last()]),
        }
        self.strategy['qualification_set'] = 'obj_a'

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(set(getattr(self.person_b, key).all()), value,
                             key)

    def test_merging_m2m_with_similar_attributes(self):
        """Regression test: merging people with the same M2M objects, e.g. when
        both people have task 'learner' in event 'ABCD', would result in unique
        constraint violation and cause IntegrityError."""
        self.person_b.task_set.create(
            event=Event.objects.get(slug='ends-tomorrow-ongoing'),
            role=Role.objects.get(name='instructor'),
        )

        self.strategy['task_set'] = 'combine'

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)


def github_username_to_uid_mock(username):
    username2uid = {
        'username': '1',
        'changed': '2',
        'changedagain': '3',
    }
    return username2uid[username]


class TestPersonAndUserSocialAuth(TestBase):
    """ Test Person.synchronize_usersocialauth and Person.save."""

    @patch('workshops.github_auth.github_username_to_uid',
           github_username_to_uid_mock)
    def test_basic(self):
        user = Person.objects.create_user(
            username='user', personal='Typical', family='User',
            email='undo@example.org', password='user',
        )

        # Syncing UserSocialAuth for a user without GitHub username should
        # not create any UserSocialAuth record.
        user.github = ''
        user.save()
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list('provider', 'uid', 'user')
        expected = []
        self.assertSequenceEqual(got, expected)

        # UserSocialAuth record should be created for a user with GitHub
        # username.
        user.github = 'username'
        user.save()
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list('provider', 'uid', 'user')
        expected = [('github', '1', user.pk)]
        self.assertSequenceEqual(got, expected)

        # When GitHub username is changed, Person.save should take care of
        # clearing UserSocialAuth table.
        user.github = 'changed'
        user.save()

        expected = []
        got = UserSocialAuth.objects.values_list('provider', 'uid', 'user')
        self.assertSequenceEqual(got, expected)

        # Syncing UserSocialAuth should result in a new UserSocialAuth record.
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list('provider', 'uid', 'user')
        expected = [('github', '2', user.pk)]
        self.assertSequenceEqual(got, expected)

        # Syncing UserSocialAuth after changing GitHub username without
        # saving should also result in updated UserSocialAuth.
        user.github = 'changedagain'
        # no user.save()
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list('provider', 'uid', 'user')
        expected = [('github', '3', user.pk)]
        self.assertSequenceEqual(got, expected)

    def test_errors_are_not_hidden(self):
        """ Test that errors occuring in synchronize_usersocialauth are not
        hidden, that is you're not redirected to any other view. Regression
        for #890. """

        self._setUpUsersAndLogin()
        with patch.object(Person, 'synchronize_usersocialauth',
                          side_effect=NotImplementedError):
            with self.assertRaises(NotImplementedError):
                self.client.get(reverse('sync_usersocialauth',
                                        args=(self.admin.pk,)))

