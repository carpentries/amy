from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from rq.exceptions import NoSuchJobError

from autoemails import admin
from autoemails.actions import NewInstructorAction
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.job import Job
from autoemails.tests.base import FakeRedisTestCaseMixin, dummy_job
from workshops.models import Event, Organization, Person, Role, Task
from workshops.tests.base import SuperuserMixin


class TestAdminJobReschedule(SuperuserMixin, FakeRedisTestCaseMixin, TestCase):
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

        self.new_template = "Welcome to AMY!"

        # test event and task
        LC_org = Organization.objects.create(
            domain="librarycarpentry.org", fullname="Library Carpentry"
        )
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=LC_org,
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        p = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        r = Role.objects.create(name="instructor")
        self.task = Task.objects.create(event=self.event, person=p, role=r)

    def tearDown(self):
        super().tearDown()
        # bring back saved scheduler
        admin.scheduler = self._saved_scheduler

    def test_view_doesnt_allow_GET(self):
        # log admin user
        self._logSuperuserIn()

        url = reverse("admin:autoemails_rqjob_edit_template", args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 405)  # Method not allowed

    def test_view_access_by_anonymous(self):
        url = reverse("admin:autoemails_rqjob_edit_template", args=[self.rqjob.pk])
        rv = self.client.post(url)
        self.assertEqual(rv.status_code, 302)
        # cannot check by assertRedirect because there's additional `?next`
        # parameter
        self.assertTrue(rv.url.startswith(reverse("login")))

    def test_view_access_by_admin(self):
        # log admin user
        self._logSuperuserIn()

        # try accessing the view again
        url = reverse("admin:autoemails_rqjob_edit_template", args=[self.rqjob.pk])
        rv = self.client.post(url)
        self.assertEqual(rv.status_code, 302)
        self.assertRedirects(
            rv, reverse("admin:autoemails_rqjob_preview", args=[self.rqjob.pk])
        )

    def test_no_such_job(self):
        # log admin user
        self._logSuperuserIn()

        with self.assertRaises(NoSuchJobError):
            Job.fetch(self.rqjob.job_id, connection=self.scheduler.connection)

        url = reverse("admin:autoemails_rqjob_edit_template", args=[self.rqjob.pk])
        rv = self.client.post(url, follow=True)
        self.assertIn(
            "The corresponding job in Redis was probably already executed",
            rv.content.decode("utf-8"),
        )

    def test_job_not_in_scheduled_jobs_queue(self):
        # log admin user
        self._logSuperuserIn()

        # case 1: job didn't go through RQ-Scheduler, but directly to Queue
        job1 = self.queue.enqueue(dummy_job)
        rqjob1 = RQJob.objects.create(job_id=job1.id, trigger=self.trigger)
        Job.fetch(job1.id, connection=self.scheduler.connection)  # no error
        with self.connection.pipeline() as pipe:
            pipe.watch(self.scheduler.scheduled_jobs_key)
            self.assertIsNone(pipe.zscore(self.scheduler.scheduled_jobs_key, job1.id))
        url = reverse("admin:autoemails_rqjob_edit_template", args=[rqjob1.pk])
        payload = {
            "template": self.new_template,
        }
        rv = self.client.post(url, payload, follow=True)
        self.assertIn(
            f"The job {job1.id} template cannot be updated.",
            rv.content.decode("utf-8"),
        )

        # case 2: job is no longer in the RQ-Scheduler queue, but it was there!
        job2 = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )
        rqjob2 = RQJob.objects.create(job_id=job2.id, trigger=self.trigger)

        # move job to the queue so it's executed
        self.scheduler.enqueue_job(job2)
        Job.fetch(job2.id, connection=self.scheduler.connection)  # no error
        url = reverse("admin:autoemails_rqjob_edit_template", args=[rqjob2.pk])
        rv = self.client.post(url, payload, follow=True)
        self.assertIn(
            f"The job {job2.id} template cannot be updated.",
            rv.content.decode("utf-8"),
        )

    def test_job_template_updated_correctly(self):
        # log admin user
        self._logSuperuserIn()

        action = NewInstructorAction(
            self.trigger,
            objects={"event": self.event, "task": self.task},
        )
        job = self.scheduler.enqueue_in(
            timedelta(minutes=60),
            action,
        )
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)
        Job.fetch(job.id, connection=self.scheduler.connection)  # no error
        url = reverse("admin:autoemails_rqjob_edit_template", args=[rqjob.pk])
        payload = {
            "template": self.new_template,
        }
        rv = self.client.post(url, payload, follow=True)
        self.assertIn(
            f"The job {job.id} template was updated",
            rv.content.decode("utf-8"),
        )

        job.refresh()
        self.assertEqual(job.instance.template.body_template, "Welcome to AMY!")
