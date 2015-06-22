from itertools import product
from datetime import datetime

from django.core.urlresolvers import reverse

from .base import TestBase
from ..models import Task, Event, Role, Person, Site


class TestTask(TestBase):
    "Tests for the task model, its manager and views"

    def setUp(self):
        self.fixtures = {}

        test_site = Site.objects.create(domain='example.com',
                                        fullname='Test Site')

        test_person_1 = Person.objects.create(personal='Test',
                                              family='Person1',
                                              username="person1")

        test_person_2 = Person.objects.create(personal='Test',
                                              family='Person2',
                                              username="person2")

        test_event_1 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_1',
                                            site=test_site,
                                            admin_fee=0)

        test_event_2 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_2',
                                            site=test_site,
                                            admin_fee=0)

        test_event_3 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_3',
                                            site=test_site,
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
            rv = self.client.get(reverse('task_delete', args=[task.pk, ]))
            assert rv.status_code == 302

            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(pk=task.pk)
