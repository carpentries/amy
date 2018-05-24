import datetime

from django.urls import reverse

from api.test.base import APITestBase
from workshops.models import (
    Person,
    Award,
    Badge,
    Event,
    Task,
    Organization,
    Airport,
    Role,
)


class TestAPIStructure(APITestBase):
    def setUp(self):
        self.admin = Person.objects.create_superuser(
            username='admin', personal='Super', family='User',
            email='sudo@example.org', password='admin',
        )
        self.admin.data_privacy_agreement = True
        self.admin.airport = Airport.objects.first()
        self.admin.save()

        self.event = Event.objects.create(slug='test-event',
                                          host=Organization.objects.first(),
                                          administrator=Organization.objects.first(),
                                          assigned_to=self.admin)

        self.award = Award.objects.create(
            person=self.admin, badge=Badge.objects.first(), event=self.event,
        )

        self.instructor_role = Role.objects.create(name='instructor')

        self.task = Task.objects.create(event=self.event, person=self.admin,
                                        role=self.instructor_role)

        self.client.login(username='admin', password='admin')

    def test_structure_for_list_views(self):
        """Ensure we have list-type views in exact places."""
        # root
        # → persons
        #   → awards
        # → events
        #   → tasks
        #   → todos
        # → organizations
        # → airports
        # → reports
        index = self.client.get(reverse('api:root'))
        index_links = {
            'person-list': reverse('api:person-list'),
            'event-list': reverse('api:event-list'),
            'organization-list': reverse('api:organization-list'),
            'airport-list': reverse('api:airport-list'),
            'reports-list': reverse('api:reports-list'),
        }
        for endpoint, link in index_links.items():
            self.assertIn(link, index.data[endpoint])

        person = self.client.get(reverse('api:person-detail',
                                         args=[self.admin.pk]))
        person_links = {
            'awards': reverse('api:person-awards-list', args=[self.admin.pk]),
        }
        for endpoint, link in person_links.items():
            self.assertIn(link, person.data[endpoint])

        event = self.client.get(reverse('api:event-detail',
                                        args=[self.event.slug]))
        event_links = {
            'tasks': reverse('api:event-tasks-list', args=[self.event.slug]),
            'todos': reverse('api:event-todos-list', args=[self.event.slug]),
        }
        for endpoint, link in event_links.items():
            self.assertIn(link, event.data[endpoint])

    def test_structure_for_reports(self):
        """Ensure we have good links to all the reports."""
        reports = self.client.get(reverse('api:reports-list'))
        reports_links = {
            'reports-all-activity-over-time':
                reverse('api:reports-all-activity-over-time'),
            'reports-instructor-num-taught':
                reverse('api:reports-instructor-num-taught'),
            'reports-instructors-over-time':
                reverse('api:reports-instructors-over-time'),
            'reports-learners-over-time':
                reverse('api:reports-learners-over-time'),
            'reports-workshops-over-time':
                reverse('api:reports-workshops-over-time'),
        }
        for endpoint, link in reports_links.items():
            self.assertIn(link, reports.data[endpoint])

    def test_links_between_resources(self):
        # event
        #   → host-detail (via host, administrator)
        #   → tasks-list
        #   → todos-list
        #   → person-detail
        # host (no links)
        # task
        #   → person-detail
        # todos (no links)
        # person
        #   → airport-detail
        #   → award-list
        #   → task-list
        # airport (no links)
        # award
        #   → event-detail
        event = self.client.get(reverse('api:event-detail',
                                        args=[self.event.slug]))
        event_links = {
            'host': reverse('api:organization-detail', args=[self.event.host.domain]),
            'administrator': reverse('api:organization-detail',
                                     args=[self.event.administrator.domain]),
            'tasks': reverse('api:event-tasks-list', args=[self.event.slug]),
            'todos': reverse('api:event-todos-list', args=[self.event.slug]),
            'assigned_to': reverse('api:person-detail',
                                   args=[self.event.assigned_to.pk])
        }
        for attr, link in event_links.items():
            self.assertIn(link, event.data[attr])

        task = self.client.get(reverse('api:event-tasks-detail',
                                       args=[self.event.slug, self.task.pk]))
        task_links = {
            'person': reverse('api:person-detail', args=[self.admin.pk]),
        }
        for attr, link in task_links.items():
            self.assertIn(link, task.data[attr])

        person = self.client.get(reverse('api:person-detail',
                                         args=[self.admin.pk]))
        person_links = {
            'airport': reverse('api:airport-detail',
                               args=[self.admin.airport.iata]),
            'awards': reverse('api:person-awards-list', args=[self.admin.pk]),
            'tasks': reverse('api:person-tasks-list', args=[self.admin.pk]),
        }
        for attr, link in person_links.items():
            self.assertIn(link, person.data[attr])

        award = self.client.get(reverse('api:person-awards-detail',
                                        args=[self.admin.pk, self.award.pk]))
        award_links = {
            'event': reverse('api:event-detail', args=[self.award.event.slug]),
        }
        for attr, link in award_links.items():
            self.assertIn(link, award.data[attr])
