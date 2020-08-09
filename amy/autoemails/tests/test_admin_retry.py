from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from rq import Queue, SimpleWorker
from rq.exceptions import NoSuchJobError

from autoemails import admin
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.job import Job
from autoemails.tests.base import (
    FakeRedisTestCaseMixin,
    dummy_job,
    dummy_fail_job,
)
from workshops.tests.base import SuperuserMixin


class TestAdminJobRetry(SuperuserMixin, FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self._setUpSuperuser()  # creates self.admin

        # save scheduler and connection data
        self._saved_scheduler = admin.scheduler
        # overwrite
        admin.scheduler = self.scheduler

        # fake RQJob
        self.email = EmailTemplate.objects.create(slug="test-1")
        self.trigger = Trigger.objects.create(action="new-instructor",
                                              template=self.email)
        self.rqjob = RQJob.objects.create(job_id="fake-id",
                                          trigger=self.trigger)

    def tearDown(self):
        super().tearDown()
        # bring back saved scheduler
        admin.scheduler = self._saved_scheduler

    def test_view_doesnt_allow_GET(self):
        # log admin user
        self._logSuperuserIn()

        url = reverse('admin:autoemails_rqjob_retry', args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 405)  # Method not allowed

    def test_view_access_by_anonymous(self):
        url = reverse('admin:autoemails_rqjob_retry', args=[self.rqjob.pk])
        rv = self.client.post(url)
        self.assertEqual(rv.status_code, 302)
        # cannot check by assertRedirect because there's additional `?next`
        # parameter
        self.assertTrue(rv.url.startswith(reverse('login')))

    def test_view_access_by_admin(self):
        # log admin user
        self._logSuperuserIn()

        # try accessing the view again
        url = reverse('admin:autoemails_rqjob_retry', args=[self.rqjob.pk])
        rv = self.client.post(url)
        self.assertEqual(rv.status_code, 302)
        self.assertRedirects(rv, reverse('admin:autoemails_rqjob_preview',
                                         args=[self.rqjob.pk]))

    def test_no_such_job(self):
        # log admin user
        self._logSuperuserIn()

        with self.assertRaises(NoSuchJobError):
            Job.fetch(self.rqjob.job_id, connection=self.scheduler.connection)

        url = reverse('admin:autoemails_rqjob_retry', args=[self.rqjob.pk])
        rv = self.client.post(url, follow=True)
        self.assertIn(
            'The corresponding job in Redis was probably already executed',
            rv.content.decode('utf-8'),
        )

    def test_job_not_failed(self):
        # log admin user
        self._logSuperuserIn()

        # case 1: job didn't go through RQ-Scheduler, but directly to Queue
        job1 = self.queue.enqueue(dummy_job)
        rqjob1 = RQJob.objects.create(job_id=job1.id, trigger=self.trigger)
        Job.fetch(job1.id, connection=self.scheduler.connection)  # no error
        with self.connection.pipeline() as pipe:
            pipe.watch(self.scheduler.scheduled_jobs_key)
            self.assertIsNone(
                pipe.zscore(
                    self.scheduler.scheduled_jobs_key, job1.id
                )
            )
        url = reverse('admin:autoemails_rqjob_retry', args=[rqjob1.pk])
        rv = self.client.post(url, follow=True)
        self.assertIn(
            "You cannot re-try a non-failed job.",
            rv.content.decode('utf-8'),
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
        url = reverse('admin:autoemails_rqjob_retry', args=[rqjob2.pk])
        rv = self.client.post(url, follow=True)
        self.assertIn(
            "You cannot re-try a non-failed job.",
            rv.content.decode('utf-8'),
        )

    def test_job_retried_correctly(self):
        """To check if the job was correctly failed etc., we should use
        a Worker and not the queue provided with FakeRedisTestCaseMixin."""
        # Create an asynchronous queue.
        # The name `separate_queue` used here is to ensure the queue isn't used
        # anywhere else.
        queue = Queue('separate_queue', connection=self.connection)
        worker = SimpleWorker([queue], connection=queue.connection)

        # log admin user
        self._logSuperuserIn()

        # this job will fail
        job = queue.enqueue(dummy_fail_job)
        self.assertEqual(job.get_status(), 'queued')

        # log the job in our system as RQJob
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)

        # run the worker
        worker.work(burst=True)
        self.assertEqual(job.get_status(), 'failed')

        url = reverse('admin:autoemails_rqjob_retry', args=[rqjob.pk])
        rv = self.client.post(url, follow=True)
        self.assertIn(
            f'The job {job.id} was requeued. It will be run shortly.',
            rv.content.decode('utf-8'),
        )

        self.assertEqual(job.get_status(refresh=True), 'queued')
