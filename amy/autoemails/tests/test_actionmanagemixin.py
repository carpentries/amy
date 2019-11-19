from datetime import date, timedelta, datetime
from unittest.mock import MagicMock

from django.test import TestCase, RequestFactory
import django_rq
from fakeredis import FakeStrictRedis
from rq import Queue
from rq_scheduler.utils import to_unix

from autoemails.actions import NewInstructorAction
from autoemails.base_views import ActionManageMixin
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin
from workshops.models import (
    Tag,
    Event,
    Role,
    Person,
    Task,
    Organization,
)


class TestActionManageMixin(FakeRedisTestCaseMixin, TestCase):
    def testNotImplementedMethods(self):
        a = ActionManageMixin()

        with self.assertRaises(NotImplementedError):
            a.get_logger()
        with self.assertRaises(NotImplementedError):
            a.get_scheduler()
        with self.assertRaises(NotImplementedError):
            a.get_redis_connection()
        with self.assertRaises(NotImplementedError):
            a.get_triggers()
        with self.assertRaises(NotImplementedError):
            a.get_jobs()
        with self.assertRaises(NotImplementedError):
            a.objects()

    def testActionAdding(self):
        # prepare some necessary objects
        template = EmailTemplate.objects.create()
        trigger = Trigger.objects.create(action='test-action',
                                         template=template)

        # totally fake Task, Role and Event data
        Tag.objects.bulk_create([
            Tag(name='SWC'),
            Tag(name='DC'),
            Tag(name='LC'),
        ])
        event = Event.objects.create(
            slug='test-event',
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country='GB',
            venue='Ministry of Magic',
            address='Underground',
            latitude=20.0,
            longitude=20.0,
            url='https://test-event.example.com',
        )
        event.tags.set(Tag.objects.filter(name__in=['SWC', 'DC', 'LC']))
        person = Person.objects.create(personal='Harry', family='Potter',
                                       email='hp@magic.uk')
        role = Role.objects.create(name='instructor')
        task = Task.objects.create(event=event, person=person, role=role)

        # Define a special class inheriting from the mixin we're about to test
        # so that we can (indirectly?) test the mixin itself. In some cases
        # the mock mechanism will have to be used, because - again - we can
        # only indirectly test the behavior of `action_add()`.
        class MockView(ActionManageMixin):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.object = task
                self.logger = MagicMock()

            def get_logger(self):
                return self.logger

            def get_scheduler(self):
                self.queue = Queue(is_async=False,
                                   connection=self.get_redis_connection())
                self.scheduler = django_rq.get_scheduler('default',
                                                         queue=self.queue)
                return self.scheduler

            def get_redis_connection(self):
                self.connection = FakeStrictRedis()
                return self.connection

            def get_triggers(self):
                objs = [trigger]
                triggers = MagicMock()
                triggers.__iter__.return_value = iter(objs)
                triggers.count.return_value = len(objs)
                return triggers

            def objects(self):
                return dict(task=self.object, event=self.object.event)

            @property
            def request(self):
                # fake request created thanks to RequestFactory from Django
                # Test Client
                req = RequestFactory().post('/tasks/create')
                return req

        # almost identical action object to a one that is created in the view
        action = NewInstructorAction(
            trigger=trigger,
            objects=dict(task=task, event=task.event),
        )

        view = MockView()
        
        # assertions before the view action is invoked
        self.assertEqual(self.scheduler.count(), 0)
        self.assertEqual(RQJob.objects.count(), 0)

        # view action invoke
        view.action_add(NewInstructorAction)

        # ensure only one job is added (because we created only one trigger for
        # it)
        self.assertEqual(self.scheduler.count(), 1)
        jobs = list(self.scheduler.get_jobs())
        self.assertEqual(len(jobs), 1)

        # logger.debug is called 6 times
        self.assertEqual(view.get_logger().debug.call_count, 6)

        # test job
        job = jobs[0]

        # proper action is scheduled
        # accessing `instance` directly causes unppickling of stored data
        self.assertEqual(job.instance, action)

        # job appeared in the queue
        enqueued_job, enqueued_timestamp = list(self.scheduler.get_jobs(
            until=to_unix(datetime.utcnow() + action.launch_at),
            with_times=True,
        ))[0]
        self.assertEqual(job, enqueued_job)

        # job appeared in the queue with correct timestamp (we accept +- 1min)
        run_time = datetime.utcnow() + action.launch_at
        one_min = timedelta(minutes=1)
        self.assertTrue(
            (run_time + one_min) > enqueued_timestamp > (run_time - one_min)
        )

        # meta as expected
        self.assertEqual(
            job.meta,
            dict(
                action=action,
                template=template,
                launch_at=action.get_launch_at(),
                email=None,
                context=None,
            ),
        )

        # test self.rq_jobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()
        self.assertEqual(rqjob.job_id, job.get_id())
        self.assertEqual(rqjob.trigger, trigger)
