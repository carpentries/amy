import django_rq
from fakeredis import FakeStrictRedis
from redis import Redis
from rq import Queue


connection = FakeStrictRedis()


class FakeRedisTestCaseMixin:
    """TestCase mixin that provides easy setup of FakeRedis connection to both
    Django-RQ and RQ-Scheduler, as well as test-teardown with scheduled jobs
    purging."""

    def setUp(self):
        super().setUp()
        self.connection = connection
        # self.connection = Redis()
        self.queue = Queue(is_async=False, connection=self.connection)
        self.scheduler = django_rq.get_scheduler('testing', queue=self.queue)

    def tearDown(self):
        # clear job queue
        for job in self.scheduler.get_jobs():
            self.scheduler.cancel(job)
        assert not bool(list(self.scheduler.get_jobs()))
        assert self.scheduler.count() == 0
        super().tearDown()
