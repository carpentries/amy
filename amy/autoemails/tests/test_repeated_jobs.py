from django.test import TestCase

from amy.autoemails.utils import schedule_repeated_jobs
from autoemails.models import EmailTemplate, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin


class TestActionManageMixin(FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()

        # prepare some necessary objects
        self.template = EmailTemplate.objects.create()
        self.trigger = Trigger.objects.create(
            action="archive-warning", template=self.template
        )

    def testRepeatedJob(self):
        schedule_repeated_jobs(self.scheduler)
        self.assertNotEqual(list(self.scheduler.get_jobs(with_times=True)), [])
