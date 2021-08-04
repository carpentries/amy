from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

from django.test import RequestFactory, TestCase
from rq.exceptions import NoSuchJobError
from rq_scheduler.utils import to_unix

from amy.autoemails.utils import schedule_repeated_jobs
from autoemails.actions import ProfileArchivalWarningAction
from autoemails.base_views import ActionManageMixin
from autoemails.job import Job
from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin, dummy_job
from workshops.models import Event, Organization, Person, Role, Tag, Task


class TestActionManageMixin(FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()

        # prepare some necessary objects
        self.template = EmailTemplate.objects.create()
        self.trigger = Trigger.objects.create(
            action="archive-warning", template=self.template
        )

        # # totally fake Task, Role and Event data
        # Tag.objects.bulk_create(
        #     [
        #         Tag(name="SWC"),
        #         Tag(name="DC"),
        #         Tag(name="LC"),
        #     ]
        # )
        # self.event = Event.objects.create(
        #     slug="test-event",
        #     host=Organization.objects.first(),
        #     start=date.today() + timedelta(days=7),
        #     end=date.today() + timedelta(days=8),
        #     country="GB",
        #     venue="Ministry of Magic",
        #     address="Underground",
        #     latitude=20.0,
        #     longitude=20.0,
        #     url="https://test-event.example.com",
        # )
        # self.event.tags.set(Tag.objects.filter(name__in=["SWC", "DC", "LC"]))
        # self.person = Person.objects.create(
        #     personal="Harry", family="Potter", email="hp@magic.uk"
        # )
        # self.role = Role.objects.create(name="instructor")
        # self.task = Task.objects.create(
        #     event=self.event, person=self.person, role=self.role
        # )

    def testRepeatedJob(self):
        schedule_repeated_jobs(self.scheduler)
        self.assertNotEqual(list(self.scheduler.get_jobs(with_times=True)), [])
