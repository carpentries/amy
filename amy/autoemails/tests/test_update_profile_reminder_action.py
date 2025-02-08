from datetime import timedelta

from django.test import TestCase, tag
from django.utils import timezone

import autoemails.actions
from autoemails.actions import (
    ProfileUpdateReminderAction,
    UpdateProfileReminderRepeatedAction,
)
from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin
from workshops.models import Person


@tag("autoemails")
class TestUpdateProfileRepeatedAction(FakeRedisTestCaseMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        trigger = Trigger.objects.create(
            action="profile-update", template=EmailTemplate.objects.create()
        )
        self.action = UpdateProfileReminderRepeatedAction(trigger=trigger)

        # save scheduler and connection data
        self._saved_scheduler = autoemails.actions.scheduler
        # overwrite them
        autoemails.actions.scheduler = self.scheduler

    def tearDown(self):
        super().tearDown()
        autoemails.actions.scheduler = self._saved_scheduler

    def test_action(self) -> None:
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p2 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            username="hgranger",
            email="hg@magic.uk",
            is_active=True,
        )
        p3 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="rweasley",
            email="rw@magic.uk",
            is_active=True,
        )
        p3.created_at = timezone.now() - timedelta(days=9)
        p3.save()
        self.action()
        rq_jobs = RQJob.objects.filter(trigger=self.action.trigger)
        self.assertCountEqual([job.recipients for job in rq_jobs], [p1.email, p2.email])
        for job in rq_jobs:
            self.assertEqual(job.action_name, ProfileUpdateReminderAction.__name__)
