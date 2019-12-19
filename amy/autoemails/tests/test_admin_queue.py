from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
import django_rq
from fakeredis import FakeStrictRedis
from rq import Queue

from autoemails import admin
from autoemails.tests.base import FakeRedisTestCaseMixin
from workshops.tests.base import SuperuserMixin


def dummy_job():
    return 42


class TestAdminQueueView(SuperuserMixin, FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('admin:autoemails_emailtemplate_queue')
        self._setUpSuperuser()  # creates self.admin

        # save scheduler and connection data
        self._saved_scheduler = admin.scheduler
        # overwrite
        admin.scheduler = self.scheduler

    def tearDown(self):
        super().tearDown()
        # bring back saved scheduler
        admin.scheduler = self._saved_scheduler

    def test_view_access_by_anonymous(self):
        rv = self.client.get(self.url)
        self.assertNotEqual(rv.status_code, 200)

    def test_view_access_by_admin(self):
        # log admin user
        self._logSuperuserIn()

        # try accessing the view again
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)

    def test_empty_queue(self):
        # log admin user
        self._logSuperuserIn()

        # access the queue view
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)

        # make sure there were no jobs listed
        self.assertEqual(rv.context['queue'], [])

    def test_not_empty_queue(self):
        # log admin user
        self._logSuperuserIn()

        # access the queue view
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)

        # make sure we start with no jobs listed
        self.assertEqual(rv.context['queue'], [])

        # schedule some dummy job
        job = self.scheduler.enqueue_in(timedelta(hours=1), dummy_job)
        self.assertNotEqual(list(self.scheduler.get_jobs(with_times=True)), [])

        # refresh queue list
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)
        self.assertNotEqual(rv.context['queue'], [])

        # first element contains a pair of (job, scheduled time)
        queue = rv.context['queue']
        job2, time = queue[0]
        self.assertEqual(job, job2)
