from django.urls import reverse
from rest_framework.test import APITestCase

from consents.models import Consent, Term
from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    Organization,
    Person,
    Role,
    Task,
)
from workshops.tests.base import consent_to_all_required_consents


class TestAPIStructure(APITestCase):
    def setUp(self):
        self.admin = Person.objects.create_superuser(
            username="admin",
            personal="Super",
            family="User",
            email="sudo@example.org",
            password="admin",
        )
        consent_to_all_required_consents(self.admin)
        self.admin.airport = Airport.objects.first()
        self.admin.save()

        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.first(),
            assigned_to=self.admin,
        )

        self.award = Award.objects.create(
            person=self.admin,
            badge=Badge.objects.first(),
            event=self.event,
        )
        self.term = Term.objects.active().prefetch_active_options()[0]
        old_consent = Consent.objects.filter(
            person=self.admin,
            term=self.term,
        ).active()[0]
        self.consent = Consent.reconsent(consent=old_consent, term_option=self.term.options[0])

        self.instructor_role = Role.objects.create(name="instructor")

        self.task = Task.objects.create(event=self.event, person=self.admin, role=self.instructor_role)

        self.client.login(username="admin", password="admin")

    def test_structure_for_list_views(self):
        """Ensure we have list-type views in exact places."""
        # root
        # → persons
        #   → awards
        # → events
        #   → tasks
        # → organizations
        # → airports
        # → reports
        index = self.client.get(reverse("api-v1:root"))
        index_links = {
            "person-list": reverse("api-v1:person-list"),
            "term-list": reverse("api-v1:term-list"),
            "event-list": reverse("api-v1:event-list"),
            "organization-list": reverse("api-v1:organization-list"),
            "airport-list": reverse("api-v1:airport-list"),
        }
        for endpoint, link in index_links.items():
            self.assertIn(link, index.data[endpoint])

        person = self.client.get(reverse("api-v1:person-detail", args=[self.admin.pk]))
        person_links = {
            "awards": reverse("api-v1:person-awards-list", args=[self.admin.pk]),
        }
        for endpoint, link in person_links.items():
            self.assertIn(link, person.data[endpoint])

        event = self.client.get(reverse("api-v1:event-detail", args=[self.event.slug]))
        event_links = {
            "tasks": reverse("api-v1:event-tasks-list", args=[self.event.slug]),
        }
        for endpoint, link in event_links.items():
            self.assertIn(link, event.data[endpoint])

    def test_links_between_resources(self):
        # event
        #   → host-detail (via host, administrator)
        #   → tasks-list
        #   → person-detail
        # host (no links)
        # task
        #   → person-detail
        # person
        #   → airport-detail
        #   → award-list
        #   → task-list
        #   → consent-list
        # consent
        #   → person-detail
        # airport (no links)
        # award
        #   → event-detail
        event = self.client.get(reverse("api-v1:event-detail", args=[self.event.slug]))
        event_links = {
            "host": reverse("api-v1:organization-detail", args=[self.event.host.domain]),
            "administrator": reverse("api-v1:organization-detail", args=[self.event.administrator.domain]),
            "tasks": reverse("api-v1:event-tasks-list", args=[self.event.slug]),
            "assigned_to": reverse("api-v1:person-detail", args=[self.event.assigned_to.pk]),
        }
        for attr, link in event_links.items():
            self.assertIn(link, event.data[attr])

        task = self.client.get(reverse("api-v1:event-tasks-detail", args=[self.event.slug, self.task.pk]))
        task_links = {
            "person": reverse("api-v1:person-detail", args=[self.admin.pk]),
        }
        for attr, link in task_links.items():
            self.assertIn(link, task.data[attr])

        person = self.client.get(reverse("api-v1:person-detail", args=[self.admin.pk]))
        person_links = {
            "airport": reverse("api-v1:airport-detail", args=[self.admin.airport.iata]),
            "awards": reverse("api-v1:person-awards-list", args=[self.admin.pk]),
            "tasks": reverse("api-v1:person-tasks-list", args=[self.admin.pk]),
            "consents": reverse("api-v1:person-consents-list", args=[self.admin.pk]),
        }
        for attr, link in person_links.items():
            self.assertIn(link, person.data[attr])

        award = self.client.get(reverse("api-v1:person-awards-detail", args=[self.admin.pk, self.award.pk]))
        award_links = {
            "event": reverse("api-v1:event-detail", args=[self.award.event.slug]),
        }
        for attr, link in award_links.items():
            self.assertIn(link, award.data[attr])
