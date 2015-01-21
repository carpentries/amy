from django.test import TestCase
from django.core.urlresolvers import reverse
from datetime import datetime
from ..models import Task, Event, Role, Person, Site

class TestTask(TestCase):
    "Tests for the task model, its manager and views"

    def setUp(self):
        self.fixtures = {}

        test_site = Site.objects.create(domain='example.com',
                 fullname='Test Site')

        test_person_1 = Person.objects.create(personal='Test',
                                              family='Person1')

        test_person_2 = Person.objects.create(personal='Test',
                                              family='Person2')

        test_event_1 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_1',
                                            site=test_site,
                                            admin_fee=0)

        test_event_2 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_2',
                                            site=test_site,
                                            admin_fee=0)

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
