import django_rq
from fakeredis import FakeStrictRedis
from rq import Queue


class FakeRedisTestCaseMixin:
    """TestCase mixin that provides easy setup of FakeRedis connection to both
    Django-RQ and RQ-Scheduler, as well as test-teardown with scheduled jobs
    purging."""

    def setUp(self):
        super().setUp()
        self.connection = FakeStrictRedis()
        self.queue = Queue(is_async=False, connection=self.connection)
        self.scheduler = django_rq.get_scheduler('default', queue=self.queue)

    def tearDown(self):
        super().tearDown()
        # clear job queue
        for job in self.scheduler.get_jobs():
            self.scheduler.cancel(job)
