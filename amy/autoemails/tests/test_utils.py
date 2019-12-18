from datetime import timedelta, datetime

from django.test import TestCase, override_settings
from django_rq import get_scheduler
import pytz
from rq_scheduler.utils import to_unix

from autoemails.utils import scheduled_execution_time
from autoemails.tests.base import FakeRedisTestCaseMixin


# dummy function for enqueueing
def dummy():
    return 42


class TestScheduledExecutionTime(FakeRedisTestCaseMixin, TestCase):
    def test_time_for_nonexisting_job(self):
        job_id = "doesn't exists"
        rv = scheduled_execution_time(job_id, self.scheduler)
        self.assertEqual(rv, None)

    def test_time_for_scheduled_job(self):
        # add job
        job = self.scheduler.enqueue_in(
            timedelta(minutes=5),
            dummy,
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
            dummy,
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
            dummy,
        )
        job_id = job.get_id()

        # test
        rv = scheduled_execution_time(job_id, self.scheduler, naive=True)
        self.assertEqual(rv.tzinfo, None)

        rv = scheduled_execution_time(job_id, self.scheduler, naive=False)
        self.assertEqual(rv.tzinfo, pytz.UTC)
