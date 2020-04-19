from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq_scheduler.utils import to_unix

from autoemails import admin
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin, dummy_job
from workshops.tests.base import SuperuserMixin


class TestAdminJobCancel(SuperuserMixin, FakeRedisTestCaseMixin, TestCase):
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

    def test_view_access_by_anonymous(self):
        url = reverse('admin:autoemails_rqjob_cancel', args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 302)
        # cannot check by assertRedirect because there's additional `?next`
        # parameter
        self.assertTrue(rv.url.startswith(reverse('login')))

    def test_view_access_by_admin(self):
        # log admin user
        self._logSuperuserIn()

        # try accessing the view again
        url = reverse('admin:autoemails_rqjob_cancel', args=[self.rqjob.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 302)
        self.assertRedirects(rv, reverse('admin:autoemails_rqjob_preview',
                                         args=[self.rqjob.pk]))

    def test_no_such_job(self):
        # log admin user
        self._logSuperuserIn()

        with self.assertRaises(NoSuchJobError):
            Job.fetch(self.rqjob.job_id, connection=self.scheduler.connection)

        url = reverse('admin:autoemails_rqjob_cancel', args=[self.rqjob.pk])
        rv = self.client.get(url, follow=True)
        self.assertIn(
            'The corresponding job in Redis was probably already executed',
            rv.content.decode('utf-8'),
        )

    def test_job_executed(self):
        """Ensure executed job is discovered."""
        # log admin user
        self._logSuperuserIn()

        # enqueue and then create an RQJob
        job = self.queue.enqueue(dummy_job)
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)
        Job.fetch(job.id, connection=self.scheduler.connection)  # no error
        with self.connection.pipeline() as pipe:
            pipe.watch(self.scheduler.scheduled_jobs_key)
            # no jobs in scheduler
            self.assertIsNone(
                pipe.zscore(
                    self.scheduler.scheduled_jobs_key, job.id
                )
            )

        url = reverse('admin:autoemails_rqjob_cancel', args=[rqjob.pk])
        rv = self.client.get(url, follow=True)
        self.assertIn(
            'Job has unknown status or was already executed.',
            rv.content.decode('utf-8'),
        )

    def test_enqueued_job_cancelled(self):
        """Ensure enqueued job is successfully cancelled."""
        # log admin user
        self._logSuperuserIn()

        # enqueue a job to run in future
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)

        # fetch job data
        job = Job.fetch(rqjob.job_id, connection=self.scheduler.connection)

        # `None` status is characteristic to scheduler-queued jobs.
        # Jobs added to the queue without scheduler will have different
        # status.
        self.assertEqual(job.get_status(), None)

        # the job is in scheduler's queue
        with self.connection.pipeline() as pipe:
            pipe.watch(self.scheduler.scheduled_jobs_key)
            # job in scheduler
            self.assertIsNotNone(
                pipe.zscore(
                    self.scheduler.scheduled_jobs_key, job.id
                )
            )

        # cancel the job
        url = reverse('admin:autoemails_rqjob_cancel', args=[rqjob.pk])
        rv = self.client.get(url, follow=True)
        self.assertIn(
            f'The job {rqjob.job_id} was cancelled.',
            rv.content.decode('utf-8'),
        )

        # the job is no longer in scheduler's queue
        with self.connection.pipeline() as pipe:
            pipe.watch(self.scheduler.scheduled_jobs_key)
            # job in scheduler
            self.assertIsNone(
                pipe.zscore(
                    self.scheduler.scheduled_jobs_key, job.id
                )
            )

        # job data still available
        Job.fetch(rqjob.job_id, connection=self.scheduler.connection)
        # ...but nothing is scheduled
        self.assertEqual(self.scheduler.count(), 0)

    def test_running_job_cancelled(self):
        """Ensure running job is not cancelled."""
        # Create an asynchronous queue.
        # The name `separate_queue` used here is to ensure the queue isn't
        # used anywhere else.
        queue = Queue('separate_queue', connection=self.connection)

        # log admin user
        self._logSuperuserIn()

        # add job to the queue
        job = queue.enqueue(dummy_job)
        self.assertEqual(job.get_status(), 'queued')

        # log the job in our system as RQJob
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)

        # force the job status to be "started"
        job.set_status('started')
        self.assertTrue(job.is_started)

        url = reverse('admin:autoemails_rqjob_cancel', args=[rqjob.pk])
        rv = self.client.get(url, follow=True)
        self.assertIn(
            f'Job {rqjob.job_id} has started and cannot be cancelled.',
            rv.content.decode('utf-8'),
        )

    def test_other_status_job(self):
        """Ensure jobs with other statuses are handled."""
        # Create an asynchronous queue.
        # The name `separate_queue` used here is to ensure the queue isn't
        # used anywhere else.
        queue = Queue('separate_queue', connection=self.connection)

        # log admin user
        self._logSuperuserIn()

        # add job to the queue
        job = queue.enqueue(dummy_job)
        self.assertEqual(job.get_status(), 'queued')

        # log the job in our system as RQJob
        rqjob = RQJob.objects.create(job_id=job.id, trigger=self.trigger)

        # force the job status to be "deferred" (could be something else,
        # except for "started" and "queued")
        job.set_status('deferred')
        self.assertTrue(job.is_deferred)

        url = reverse('admin:autoemails_rqjob_cancel', args=[rqjob.pk])
        rv = self.client.get(url, follow=True)
        self.assertIn(
            'Job has unknown status or was already executed.',
            rv.content.decode('utf-8'),
        )
