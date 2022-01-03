from datetime import timedelta

from django.test.testcases import TestCase

from autoemails import admin
from autoemails.tests.base import FakeRedisTestCaseMixin, dummy_job

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60


class TestJobResultsLongTTL(FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()

        # save scheduler and connection data
        self._saved_scheduler = admin.scheduler
        # overwrite
        admin.scheduler = self.scheduler

    def tearDown(self):
        super().tearDown()
        # bring back saved scheduler
        admin.scheduler = self._saved_scheduler

    def test_scheduled_job_has_1yr_TTL(self):
        # Act
        job = self.scheduler.enqueue_in(timedelta(minutes=5), dummy_job)

        # Assert
        self.assertFalse(job.is_finished)  # job still hasn't run
        self.assertEqual(job.result_ttl, ONE_YEAR_IN_SECONDS)

    def test_finished_job_has_1yr_TTL(self):
        # Arrange
        job = self.scheduler.enqueue_in(timedelta(minutes=5), dummy_job)
        # Act
        self.queue.run_job(job)

        # Assert
        self.assertTrue(job.is_finished)
        self.assertEqual(job.result_ttl, ONE_YEAR_IN_SECONDS)
