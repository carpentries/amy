from django.test import TestCase
from django.core.urlresolvers import reverse
from datetime import datetime
from ..models import Task, Event, Role, Person, Project, Site

class TestTask(TestCase):
    "Tests for the task model, it's manager and views"

    def setUp(self):

        # Create a fixtures dictionary so we can reference these
        # objects from the tests

        self.fixtures = {}

        # Create a test site
        test_site = Site.objects.create(domain='example.com',
                 fullname='Test Site')

        # Create a test project
        test_project = Project.objects.create(slug='test',
                       name='Test Project',
                       details='my test project')

        # Create two test people
        test_person_1 = Person.objects.create(personal='Test',
                                              family='Person1')

        test_person_2 = Person.objects.create(personal='Test',
                                              family='Person2')

        # Create two test events
        test_event_1 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_1',
                                            site=test_site,
                                            project=test_project,
                                            admin_fee=0)

        test_event_2 = Event.objects.create(start=datetime.now(),
                                            slug='test_event_2',
                                            site=test_site,
                                            project=test_project,
                                            admin_fee=0)

        # Create two test roles

        test_role_1 = Role.objects.create(name='test_role_1')
        test_role_2 = Role.objects.create(name='test_role_2')

        # Finally, create two tasks to test

        test_task_1 = Task.objects.create(person=test_person_1,
                                          event=test_event_1,
                                          role=test_role_1)

        test_task_2 = Task.objects.create(person=test_person_2,
                                          event=test_event_2,
                                          role=test_role_2)

        self.fixtures['test_task_1'] = test_task_1
        self.fixtures['test_task_2'] = test_task_2

    def test_task_has_detail_view(self):
        """Test that the detail view for a task is reachable
        by specifying the event, person and role.
        """

        correct_task = self.fixtures['test_task_1']

        url_kwargs = {'event_slug': correct_task.event.slug,
                      'person_id': correct_task.person.pk,
                      'role_name': correct_task.role.name}

        response = self.client.get(reverse('task_details',
                                   kwargs=url_kwargs))

        # Check whether the view has the right task associated
        assert response.context['task'].pk == correct_task.pk

    def test_task_has_edit_view(self):
        """Test that the edit view for a task is reachable
        by specifying the event, person and role.
        """

        correct_task = self.fixtures['test_task_1']

        url_kwargs = {'event_slug': correct_task.event.slug,
                      'person_id': correct_task.person.pk,
                      'role_name': correct_task.role.name}

        response = self.client.get(reverse('task_edit',
                                   kwargs=url_kwargs))

        # Check whether the view has the right task associated
        assert response.context['task'].pk == correct_task.pk
