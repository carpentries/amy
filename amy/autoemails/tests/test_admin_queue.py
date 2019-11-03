from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
import django_rq

from workshops.tests.base import SuperuserMixin


scheduler = django_rq.get_scheduler('default')


def dummy_job():
    return 42


class TestAdminQueueView(SuperuserMixin, TestCase):
    def setUp(self):
        self.url = reverse('admin:autoemails_emailtemplate_queue')
        self._setUpSuperuser()  # creates self.admin

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
        # WARNING: this uses real queue for the tests...
        # for now the tested code (admin's email queue view) doesn't have
        # option to switch to a FakeRedis server provided by us, so we
        # use the "default" scheduler.
        job = scheduler.enqueue_in(timedelta(hours=1), dummy_job)

        # refresh queue list
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)
        self.assertNotEqual(rv.context['queue'], [])

        # first element contains a pair of (job, scheduled time)
        queue = rv.context['queue']
        job2, time = queue[0]
        self.assertEqual(job, job2)

        # remove the job
        job.delete()
