from itertools import product
from datetime import datetime

from django.core.urlresolvers import reverse
from django.db import IntegrityError

from .base import TestBase
from ..models import Task, Event, Role, Person, Organization


class TestTask(TestBase):
    "Tests for the task model, its manager and views"

    def setUp(self):
        self.fixtures = {}

        test_host = Organization.objects.create(domain='example.com',
                                        fullname='Test Organization')

        test_person_1 = Person.objects.create(personal='Test',
                                              family='Person1',
                                              username="person1")

        test_person_2 = Person.objects.create(personal='Test',
                                              family='Person2',
                                              username="person2")

        test_event_1 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_1',
                                            host=test_host,
                                            admin_fee=0)

        test_event_2 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_2',
                                            host=test_host,
                                            admin_fee=0)

        test_event_3 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_3',
                                            host=test_host,
                                            admin_fee=0)

        instructor_role = Role.objects.create(name="instructor")
        learner_role = Role.objects.create(name="learner")
        helper_role = Role.objects.create(name="helper")
        roles = [instructor_role, learner_role, helper_role]
        people = [test_person_1, test_person_2]

        for role, person in product(roles, people):
            Task.objects.create(person=person, role=role, event=test_event_3)

        test_role_1 = Role.objects.create(name='test_role_1')
        test_role_2 = Role.objects.create(name='test_role_2')

        test_task_1 = Task.objects.create(person=test_person_1,
                                          event=test_event_1,
                                          role=test_role_1)

        test_task_2 = Task.objects.create(person=test_person_2,
                                          event=test_event_2,
                                          role=test_role_2)

        self.fixtures['test_task_1'] = test_task_1
        self.fixtures['test_task_2'] = test_task_2

        self._setUpUsersAndLogin()

    def test_task_detail_view_reachable_from_event_person_and_role_of_task(self):

        correct_task = self.fixtures['test_task_1']
        response = self.client.get(reverse('task_details', args=[str(correct_task.id)]))
        assert response.context['task'].pk == correct_task.pk

    def test_add_task_with_correct_url(self):
        '''Ensure that task can be saved with correct URL field'''
        task = self.fixtures['test_task_1']
        payload = {
            'event': task.event.pk,
            'person': task.person.pk,
            'role': task.role.pk,
            'title': 'Task title',
            'url': 'http://example.org',
        }
        response = self.client.post(
            reverse('task_edit', kwargs={'task_id':task.pk}),
            payload,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('task_details', kwargs={'task_id':task.pk})
        )
        task.refresh_from_db()
        self.assertEqual(task.url, 'http://example.org')
        self.assertEqual(response.context['task'].url, 'http://example.org')

    def test_add_task_with_incorrect_url(self):
        '''Ensure that a task object cannot be saved with incorrect URL field'''
        task = self.fixtures['test_task_1']
        payload = {
            'event': task.event.pk,
            'person': task.person.pk,
            'role': task.role.pk,
            'title': 'Task title',
            'url': 'htp://example.org',
        }
        response = self.client.post(
            reverse('task_edit', kwargs={'task_id':task.pk}),
            payload,
        )
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.url, '')

    def test_add_duplicate_task(self):
        '''Ensure that duplicate tasks with empty url field cannot exist'''
        task_1 = self.fixtures['test_task_1']
        with self.assertRaises(IntegrityError):
            Task.objects.create(
                event=task_1.event,
                person=task_1.person,
                role=task_1.role,
            )

    def test_add_duplicate_task_with_url(self):
        '''Ensure that duplicate tasks cannot exist'''
        task_1 = self.fixtures['test_task_1']
        task_1.url = 'http://example.org'
        task_1.save()
        with self.assertRaises(IntegrityError):
            Task.objects.create(
                event=task_1.event,
                person=task_1.person,
                role=task_1.role,
                url=task_1.url,
            )

    def test_task_edit_view_reachable_from_event_person_and_role_of_task(self):
        correct_task = self.fixtures['test_task_1']
        url_kwargs = {'task_id': correct_task.id}
        response = self.client.get(reverse('task_edit',
                                   kwargs=url_kwargs))
        assert response.context['task'].pk == correct_task.pk

    def test_task_manager_roles_lookup(self):
        """Test TaskManager methods for looking up roles by names."""
        event = Event.objects.get(slug='test_event_3')
        instructors = event.task_set.instructors()
        learners = event.task_set.learners()
        helpers = event.task_set.helpers()
        tasks = event.task_set.all()

        assert set(tasks) == set(instructors) | set(learners) | set(helpers)

    def test_delete_task(self):
        """Make sure deleted task is longer accessible."""
        for task in Task.objects.all():
            rv = self.client.post(reverse('task_delete', args=[task.pk, ]))
            assert rv.status_code == 302

            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(pk=task.pk)
