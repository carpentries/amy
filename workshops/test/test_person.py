# coding: utf-8

import datetime

from django.contrib.auth import authenticate
from django.core.urlresolvers import reverse
from django.core.validators import ValidationError
from django.contrib.auth.models import Permission, Group

from django.test import TransactionTestCase

from ..forms import PersonForm
from ..models import (
    Person, Task, Qualification, Award, Role, Event, KnowledgeDomain, Badge,
    Lesson, Host
)
from ..util import merge_persons
from .base import TestBase


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
        event = Event.objects.create(slug='test-event', host=self.host_alpha)
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


class TestPersonPassword(TestBase):
    """Separate tests for testing password setting.

    They need to be in separate class that doesn't call
    self._setUpUsersAndLogin().
    """

    def setUp(self):
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


class TestPersonMerge(TestBase):
    """Test various scenarios for merging people."""

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

        self.person1 = Person.objects.create(personal='Test',
                                             family='Person1',
                                             username='tp1')
        self.person2 = Person.objects.create(personal='Test',
                                             family='Person2',
                                             username='tp2')

        self.role1 = Role.objects.create(name='Role1')
        self.role2 = Role.objects.create(name='Role2')

        self.badge1 = Badge.objects.create(name='Badge1')
        self.badge2 = Badge.objects.create(name='Badge2')

        self.lesson1 = Lesson.objects.get(name='dc/spreadsheets')
        self.lesson2 = Lesson.objects.get(name='swc/python')

        self.domain1 = KnowledgeDomain.objects.get(pk=1)  # space sciences
        self.domain2 = KnowledgeDomain.objects.get(pk=2)  # geo* sciences

        self.event1 = Event.objects.create(slug='event1', host=self.host_alpha)
        self.event2 = Event.objects.create(slug='event2', host=self.host_beta)

    def test_nonexisting_persons(self):
        """Make sure we handle wrong user input correctly."""
        data = {
            'person_from_0': 'First person',
            'person_from_1': 1000,
            'person_to_0': 'Second person',
            'person_to_1': 2000,
        }
        rv = self.client.post(reverse('person_merge'), data, follow=True)
        content = rv.content.decode('utf-8')
        assert 'Fix errors below' in content

        session = self.client.session
        combinations = [(1000, 2000), (1000, self.ron.pk), (self.ron.pk, 2000)]
        for person_from, person_to in combinations:
            session['person_from'] = person_from
            session['person_to'] = person_to
            session.save()

            rv = self.client.get(reverse('person_merge_confirmation'))
            assert rv.status_code == 404

    def test_existing_persons(self):
        """Make sure we allow selecting existing persons."""
        data = {
            'person_from_0': '',
            'person_from_1': self.ron.pk,
            'person_to_0': '',
            'person_to_1': self.hermione.pk,
        }
        rv = self.client.post(reverse('person_merge'), data, follow=True)
        content = rv.content.decode('utf-8')
        assert 'Fix errors below' not in content
        assert self.ron.personal in content
        assert self.hermione.personal in content

        session = self.client.session
        session['person_from'] = self.ron.pk
        session['person_to'] = self.hermione.pk
        session.save()

        rv = self.client.get(reverse('person_merge_confirmation'))
        assert rv.status_code == 200

    def test_same_person(self):
        """Make sure we forbid selecting 2x the same person."""
        msg = 'Cannot merge a person with themselves'

        data = {
            'person_from_0': '',
            'person_from_1': self.ron.pk,
            'person_to_0': '',
            'person_to_1': self.ron.pk,
        }
        rv = self.client.post(reverse('person_merge'), data, follow=True)
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert 'Fix errors below' not in content
        assert msg in content

        session = self.client.session
        session['person_from'] = self.ron.pk
        session['person_to'] = self.ron.pk
        session.save()

        rv = self.client.get(reverse('person_merge_confirmation'), follow=True)
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert 'Fix errors below' not in content
        assert msg in content

    def test_merging_no_related(self):
        """Make sure actual merging works correctly.

        Test for people without any awards (badges), qualifications (lessons),
        tasks (roles) or domains.
        """
        session = self.client.session
        session['person_from'] = self.person1.pk
        session['person_to'] = self.person2.pk
        session.save()
        rv = self.client.get(reverse('person_merge_confirmation'),
                             {'confirmed': 1}, follow=True)
        assert rv.status_code == 200

        Person.objects.get(pk=self.person2.pk)
        with self.assertRaises(Person.DoesNotExist):
            Person.objects.get(pk=self.person1.pk)

    def test_merging_disjoint_related(self):
        """Make sure actual merging works correctly.

        Test for people with disjoint badges, lessons, roles, and domains.
        """
        self.person1.award_set.create(badge=self.badge1,
                                      awarded=datetime.date.today())
        self.person2.award_set.create(badge=self.badge2,
                                      awarded=datetime.date.today())
        self.person1.qualification_set.create(lesson=self.lesson1)
        self.person2.qualification_set.create(lesson=self.lesson2)
        self.person1.task_set.create(event=self.event1, role=self.role1)
        self.person2.task_set.create(event=self.event2, role=self.role2)
        self.person1.domains = [self.domain1]
        self.person2.domains = [self.domain2]

        # using the utility function without accessing the view
        # because the view was tested in previous tests
        merge_persons(self.person1, self.person2)

        p = Person.objects.get(pk=self.person2.pk)
        with self.assertRaises(Person.DoesNotExist):
            Person.objects.get(pk=self.person1.pk)

        self.assertEqual([self.badge1, self.badge2], list(p.badges.all()))
        assert Task.objects.filter(person=p, role=self.role1)
        assert Task.objects.filter(person=p, role=self.role2)
        self.assertEqual([self.domain1, self.domain2], list(p.domains.all()))
        self.assertEqual([self.lesson1, self.lesson2], list(p.lessons.all()))


class TestPersonMergeNonTransactional(TransactionTestCase):
    """Test various scenarios for merging people in transaction-disabled
    environment.

    IntegrityError run in 'normal' TestCase prevents anything from running.
    But we're using duck typing in `merge_persons` to catch unique constraint
    errors.  So this test case won't run within `atomic` block and therefore
    allow us to test `merge_people` extensively."""

    def test_merging_overlapping_related(self):
        """Make sure actual merging works correctly.

        Test for people with overlapping badges, lessons, roles and domains.
        """
        # set up
        self.person1 = Person.objects.create(personal='Test',
                                             family='Person1',
                                             username='tp1')
        self.person2 = Person.objects.create(personal='Test',
                                             family='Person2',
                                             username='tp2')

        self.host_alpha = Host.objects.create(domain='alpha.edu',
                                              fullname='Alpha Host')

        self.host_beta = Host.objects.create(domain='beta.com',
                                             fullname='Beta Host')

        self.role1 = Role.objects.create(name='Role1')
        self.role2 = Role.objects.create(name='Role2')

        self.badge1 = Badge.objects.create(name='Badge1')

        self.lesson1 = Lesson.objects.get(name='swc/python')

        self.domain1 = KnowledgeDomain.objects.get(pk=1)  # space sciences

        self.event1 = Event.objects.create(slug='event1', host=self.host_alpha)
        self.event2 = Event.objects.create(slug='event2', host=self.host_beta)

        # assign
        self.person1.award_set.create(badge=self.badge1,
                                      awarded=datetime.date.today())
        self.person2.award_set.create(badge=self.badge1,
                                      awarded=datetime.date.today())
        self.person1.qualification_set.create(lesson=self.lesson1)
        self.person2.qualification_set.create(lesson=self.lesson1)
        self.person1.task_set.create(event=self.event1, role=self.role1)
        self.person1.task_set.create(event=self.event2, role=self.role1)
        self.person2.task_set.create(event=self.event1, role=self.role2)
        self.person2.task_set.create(event=self.event2, role=self.role1)
        self.person1.domains = [self.domain1]
        self.person2.domains = [self.domain1]

        # test
        merge_persons(self.person1, self.person2)

        p = Person.objects.get(pk=self.person2.pk)
        with self.assertRaises(Person.DoesNotExist):
            Person.objects.get(pk=self.person1.pk)

        self.assertEqual([self.badge1], list(p.badges.all()))
        assert Task.objects.filter(person=p, event=self.event1,
                                   role=self.role1).count() == 1
        assert Task.objects.filter(person=p, event=self.event1,
                                   role=self.role2).count() == 1
        assert Task.objects.filter(person=p, event=self.event2,
                                   role=self.role1).count() == 1
        self.assertEqual([self.domain1], list(p.domains.all()))
        self.assertEqual([self.lesson1], list(p.lessons.all()))
