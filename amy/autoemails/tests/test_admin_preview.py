from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from autoemails import admin
from autoemails.actions import NewInstructorAction
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin, dummy_job
from autoemails.utils import scheduled_execution_time, compare_emails
from workshops.models import (
    Tag,
    Event,
    Role,
    Person,
    Task,
    Organization,
)
from workshops.tests.base import SuperuserMixin


class TestAdminJobPreview(SuperuserMixin, FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self._setUpSuperuser()  # creates self.admin

        # save scheduler and connection data
        self._saved_scheduler = admin.scheduler
        # overwrite
        admin.scheduler = self.scheduler

        # fake RQJob
        self.email = EmailTemplate.objects.create(slug="test-1")
        self.trigger = Trigger.objects.create(
            action="new-instructor", template=self.email
        )
        self.rqjob = RQJob.objects.create(job_id="fake-id", trigger=self.trigger)

    def tearDown(self):
        super().tearDown()
        # bring back saved scheduler
        admin.scheduler = self._saved_scheduler

    def prepare_data(self):
        """Create some real data (real Event, Task, Person, or action)."""
        # totally fake Task, Role and Event data
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
            ]
        )
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
            address="Underground",
            latitude=20.0,
            longitude=20.0,
            url="https://test-event.example.com",
        )
        self.event.tags.set(Tag.objects.filter(name__in=["SWC", "DC", "LC"]))
        self.person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        self.role = Role.objects.create(name="instructor")
        self.task = Task.objects.create(
            event=self.event, person=self.person, role=self.role
        )

    def test_view_access_by_anonymous(self):
        url = reverse("admin:autoemails_rqjob_preview", args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 302)

    def test_view_access_by_admin(self):
        # log admin user
        self._logSuperuserIn()

        # try accessing the view again
        url = reverse("admin:autoemails_rqjob_preview", args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

    def test_preview_job_nonexist(self):
        # log admin user
        self._logSuperuserIn()

        url = reverse("admin:autoemails_rqjob_preview", args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # We can't fetch a non-existing Job (id: "fake-id"), so almost all
        # fields are None'd.
        self.assertEqual(rv.context["rqjob"], self.rqjob)
        self.assertEqual(rv.context["job"], None)
        self.assertEqual(rv.context["job_scheduled"], None)
        self.assertEqual(rv.context["instance"], None)
        self.assertEqual(rv.context["trigger"], None)
        self.assertEqual(rv.context["template"], None)
        self.assertEqual(rv.context["email"], None)
        self.assertEqual(rv.context["adn_context"], None)

    def test_preview_job_properties_nonexist(self):
        # create some dummy job
        job = self.queue.enqueue(dummy_job)
        self.rqjob.job_id = job.id
        self.rqjob.save()

        # log admin user
        self._logSuperuserIn()

        url = reverse("admin:autoemails_rqjob_preview", args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # We can fetch the Job (id isn't fake anymore), but almost all
        # fields are None'd.
        self.assertEqual(rv.context["rqjob"], self.rqjob)
        self.assertEqual(rv.context["job"], job)
        self.assertEqual(rv.context["job_scheduled"], None)
        self.assertEqual(rv.context["instance"], None)
        self.assertEqual(rv.context["trigger"], None)
        self.assertEqual(rv.context["template"], None)
        self.assertEqual(rv.context["email"], None)
        self.assertEqual(rv.context["adn_context"], None)

    def test_preview_scheduled_job(self):
        # prepare fake data
        self.prepare_data()

        # schedule a real job (NewInstructorAction)
        action = NewInstructorAction(
            trigger=self.trigger,
            objects=dict(event=self.event, task=self.task),
        )
        # it's important to call `action._email()`, because it prepares
        # `action.context`
        email = action._email()
        job = self.scheduler.enqueue_in(timedelta(minutes=10), action)
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)
        scheduled = scheduled_execution_time(job.id, scheduler=self.scheduler)

        # log admin user
        self._logSuperuserIn()

        url = reverse("admin:autoemails_rqjob_preview", args=[rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # We can fetch the Job, it's coming from NewInstructorAction.__call__
        self.assertEqual(rv.context["rqjob"], rqjob)
        self.assertEqual(rv.context["job"], job)
        self.assertEqual(rv.context["job_scheduled"], scheduled)
        self.assertEqual(rv.context["instance"], action)
        self.assertEqual(rv.context["trigger"], self.trigger)
        self.assertEqual(rv.context["template"], self.trigger.template)
        # can't compare emails directly, __eq__ is not implemented
        self.assertTrue(compare_emails(rv.context["email"], email))
        self.assertEqual(rv.context["adn_context"], action.context)

    def test_preview_invoked_job(self):
        # prepare fake data
        self.prepare_data()

        # schedule a real job (NewInstructorAction)
        action = NewInstructorAction(
            trigger=self.trigger,
            objects=dict(event=self.event, task=self.task),
        )
        # it's important to call `action._email()`, because it prepares
        # `action.context`
        email = action._email()
        # some cheating, normally the `action.email` is implemented in
        # `__call__`
        action.email = email

        job = self.scheduler.enqueue_in(timedelta(minutes=10), action)
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)

        # Speed up the job! Enqueue and run immediately.
        self.scheduler.enqueue_job(job)

        scheduled = scheduled_execution_time(job.id, scheduler=self.scheduler)

        # log admin user
        self._logSuperuserIn()

        url = reverse("admin:autoemails_rqjob_preview", args=[rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # We can fetch the Job, it's coming from NewInstructorAction.__call__
        self.assertEqual(rv.context["rqjob"], rqjob)
        self.assertEqual(rv.context["job"], job)
        self.assertEqual(rv.context["job_scheduled"], scheduled)
        self.assertEqual(rv.context["instance"], action)
        self.assertEqual(rv.context["trigger"], self.trigger)
        self.assertEqual(rv.context["template"], self.trigger.template)
        # can't compare emails directly, __eq__ is not implemented
        self.assertTrue(compare_emails(rv.context["email"], email))
        self.assertEqual(rv.context["adn_context"], action.context)
