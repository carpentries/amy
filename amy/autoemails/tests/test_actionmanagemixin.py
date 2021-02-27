from datetime import date, timedelta, datetime
from unittest.mock import MagicMock

from django.test import TestCase, RequestFactory
from rq.exceptions import NoSuchJobError
from rq_scheduler.utils import to_unix

from autoemails.actions import NewInstructorAction
from autoemails.base_views import ActionManageMixin
from autoemails.job import Job
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin, dummy_job
from workshops.models import (
    Tag,
    Event,
    Role,
    Person,
    Task,
    Organization,
)


class TestActionManageMixin(FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()

        # prepare some necessary objects
        self.template = EmailTemplate.objects.create()
        self.trigger = Trigger.objects.create(
            action="test-action", template=self.template
        )

        # totally fake Task, Role and Event data
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
            ]
        )
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
            address="Underground",
            latitude=20.0,
            longitude=20.0,
            url="https://test-event.example.com",
        )
        self.event.tags.set(Tag.objects.filter(name__in=["SWC", "DC", "LC"]))
        self.person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        self.role = Role.objects.create(name="instructor")
        self.task = Task.objects.create(
            event=self.event, person=self.person, role=self.role
        )

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
        trigger = self.trigger
        task = self.task

        # Define a special class inheriting from the mixin we're about to test
        # so that we can (indirectly?) test the mixin itself. In some cases
        # the mock mechanism will have to be used, because - again - we can
        # only indirectly test the behavior of `action_add()`.
        class MockView(ActionManageMixin):
            def __init__(self, connection, queue, scheduler, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.object = task
                self.logger = MagicMock()
                self.connection = connection
                self.queue = queue
                self.scheduler = scheduler

            def get_logger(self):
                return self.logger

            def get_scheduler(self):
                self.get_redis_connection()
                return self.scheduler

            def get_redis_connection(self):
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
                req = RequestFactory().post("/tasks/create")
                return req

        # almost identical action object to a one that is created in the view
        action = NewInstructorAction(
            trigger=trigger,
            objects=dict(task=task, event=task.event),
        )

        view = MockView(self.connection, self.queue, self.scheduler)

        # assertions before the view action is invoked
        self.assertEqual(self.scheduler.count(), 0)
        self.assertEqual(RQJob.objects.count(), 0)

        # view action invoke
        view.action_add(NewInstructorAction)

        # ensure only one job is added (because we created only one trigger
        # for it)
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
        enqueued_job, enqueued_timestamp = list(
            self.scheduler.get_jobs(
                until=to_unix(datetime.utcnow() + action.launch_at),
                with_times=True,
            )
        )[0]
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
                template=trigger.template,
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

    def testActionRemove(self):
        trigger = self.trigger
        task = self.task
        job_ids = MagicMock()  # it will mock a QuerySet

        # Define a special class inheriting from the mixin we're about to test
        # so that we can (indirectly?) test the mixin itself. In some cases
        # the mock mechanism will have to be used, because - again - we can
        # only indirectly test the behavior of `action_remove()`.
        class MockView(ActionManageMixin):
            def __init__(self, connection, queue, scheduler, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.object = task
                self.logger = MagicMock()
                self.connection = connection
                self.queue = queue
                self.scheduler = scheduler

            def get_logger(self):
                return self.logger

            def get_scheduler(self):
                return self.scheduler

            def get_redis_connection(self):
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
                req = RequestFactory().post("/tasks/create")
                return req

            def get_jobs(self, as_id_list=True):
                if not as_id_list:
                    raise NotImplementedError()
                return job_ids

        view = MockView(self.connection, self.queue, self.scheduler)

        # assertions before the view action is invoked
        self.assertEqual(self.scheduler.count(), 0)
        self.assertEqual(RQJob.objects.count(), 0)

        # view action invoke - it schedules a job
        view.action_add(NewInstructorAction)

        # additionally enqueue (as opposite to schedule) a blocking job
        enqueued_job = self.queue.enqueue(dummy_job)
        self.assertTrue(enqueued_job.is_finished)

        # ensure both a new Job and a corresponding RQJob were created
        self.assertEqual(self.scheduler.count(), 1)
        self.assertEqual(RQJob.objects.count(), 1)

        # ensure it's the same job
        job = next(self.scheduler.get_jobs())
        rqjob = RQJob.objects.first()
        self.assertEqual(job.get_id(), rqjob.job_id)

        # mock a Query Set
        # previously enqueued job is added here so that the action_remove
        # interface is mocked into removing it from the enqueued jobs
        real_job_ids = [job.get_id(), enqueued_job.id]
        job_ids.__iter__.return_value = iter(real_job_ids)
        job_ids.count.return_value = len(real_job_ids)

        # invoke action_remove
        view.action_remove(NewInstructorAction)

        # ensure there are no scheduled jobs nor RQJob objects
        self.assertEqual(self.scheduler.count(), 0)
        self.assertEqual(RQJob.objects.count(), 0)

        # ensure the previously enqueued job is no longer available
        with self.assertRaises(NoSuchJobError):
            Job.fetch(enqueued_job.id, connection=self.connection)

        # logger.debug is called 6 times (for action_add) and 6 times
        # (for action_remove)
        self.assertEqual(view.get_logger().debug.call_count, 6 + 6)
