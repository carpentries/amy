from datetime import timedelta, datetime

from django.test import TestCase
import pytz
from rq.queue import Queue
from rq.worker import SimpleWorker
from rq_scheduler.utils import to_unix

from autoemails.utils import (
    check_status,
    scheduled_execution_time,
)
from autoemails.tests.base import (
    FakeRedisTestCaseMixin,
    dummy_job,
    dummy_fail_job,
)


class TestScheduledExecutionTime(FakeRedisTestCaseMixin, TestCase):
    def test_time_for_nonexisting_job(self):
        job_id = "doesn't exists"
        rv = scheduled_execution_time(job_id, self.scheduler)
        self.assertEqual(rv, None)

    def test_time_for_scheduled_job(self):
        # add job
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )
        job_id = job.get_id()

        # test
        rv = scheduled_execution_time(job_id, self.scheduler)
        self.assertNotEqual(rv, None)
        epochtime = to_unix(rv)
        now = to_unix(datetime.utcnow() + timedelta(minutes=5))
        self.assertAlmostEqual(epochtime, now, delta=1)

    def test_time_for_run_job(self):
        # add job
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )
        job_id = job.get_id()

        # move the job to queue
        self.scheduler.enqueue_job(job)

        # test
        rv = scheduled_execution_time(job_id, self.scheduler)
        self.assertEqual(rv, None)

    def test_time_unaware_aware(self):
        # add job
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )
        job_id = job.get_id()

        # test
        rv = scheduled_execution_time(job_id, self.scheduler, naive=True)
        self.assertEqual(rv.tzinfo, None)

        rv = scheduled_execution_time(job_id, self.scheduler, naive=False)
        self.assertEqual(rv.tzinfo, pytz.UTC)


class TestCheckStatus(FakeRedisTestCaseMixin, TestCase):
    def test_status_nonexisting_job(self):
        job_id = "doesn't exists"
        rv = check_status(job_id, self.scheduler)
        self.assertEqual(rv, None)

    def test_status_scheduled_job(self):
        # add job
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )

        # test
        rv = check_status(job, self.scheduler)
        self.assertEqual(rv, "scheduled")

    def test_status_queued_job(self):
        # add job
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )

        # move the job to queue
        self.scheduler.enqueue_job(job)

        # test
        rv = check_status(job, self.scheduler)
        self.assertEqual(rv, "queued")

    def test_status_started_job(self):
        # Create an asynchronous queue.
        # The name `separate_queue` used here is to ensure the queue isn't
        # used anywhere else.
        queue = Queue("separate_queue", connection=self.connection)

        # add job to the queue
        job = queue.enqueue(dummy_job)
        self.assertEqual(job.get_status(), "queued")

        # force the job status to be "started"
        job.set_status("started")
        self.assertTrue(job.is_started)

        # test
        rv = check_status(job, self.scheduler)
        self.assertEqual(rv, "started")

    def test_status_failed_job(self):
        # Create an asynchronous queue.
        # The name `separate_queue` used here is to ensure the queue isn't used
        # anywhere else.
        queue = Queue("separate_queue", connection=self.connection)
        worker = SimpleWorker([queue], connection=queue.connection)

        # this job will fail
        job = queue.enqueue(dummy_fail_job)
        self.assertEqual(job.get_status(), "queued")

        # run the worker
        worker.work(burst=True)

        # test
        rv = check_status(job, self.scheduler)
        self.assertEqual(rv, "failed")

    def test_status_cancelled_job(self):
        # add job
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy_job,
        )

        # cancel job
        self.scheduler.cancel(job)

        # test
        rv = check_status(job, self.scheduler)
        self.assertEqual(rv, "cancelled")

    def test_status_deferred_job(self):
        # Create an asynchronous queue.
        # The name `separate_queue` used here is to ensure the queue isn't
        # used anywhere else.
        queue = Queue("separate_queue", connection=self.connection)

        # add job to the queue
        job = queue.enqueue(dummy_job)
        self.assertEqual(job.get_status(), "queued")

        # force the job status to be "started"
        job.set_status("deferred")
        self.assertTrue(job.is_deferred)

        # test
        rv = check_status(job, self.scheduler)
        self.assertEqual(rv, "deferred")
