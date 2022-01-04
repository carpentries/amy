from datetime import datetime
from typing import Iterable

from django.test import TestCase

from autoemails.actions import BaseAction, BaseRepeatedAction
from autoemails.management.commands.repeated_jobs import (
    REPEATED_JOBS_BY_TRIGGER,
    clear_scheduled_jobs,
    register_scheduled_jobs,
    schedule_repeating_job,
)
from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin

TEST_ACTION_NAME = "test-action"


class DummyRepeatingJob(BaseRepeatedAction):
    EMAIL_ACTION_CLASS = BaseAction
    ACTION_NAME = TEST_ACTION_NAME

    def __call__(self, *args, **kwargs):
        pass


class TestRepeatedJobsCommand(FakeRedisTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.trigger = Trigger.objects.create(
            action=TEST_ACTION_NAME,
            template=EmailTemplate.objects.create(slug="test-template"),
        )
        self.rqjob = RQJob(job_id="fake-id", trigger=self.trigger)
        self.dummy_action = BaseAction(trigger=self.trigger)

    def add_repeating_job(self) -> str:
        return schedule_repeating_job(
            self.trigger, DummyRepeatingJob, self.scheduler
        ).job_id

    def add_nonrepeating_job(self) -> str:
        """
        Schedules a non repeating dummy job to the queue
        """
        job = self.scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=self.dummy_action,
            meta={"action": self.dummy_action.__class__},
        )
        self.rqjob.job_id = job.id
        self.rqjob.save()
        return job.id

    def assert_jobs(self, job_ids: Iterable[str]) -> None:
        self.assertCountEqual(
            RQJob.objects.all().values_list("job_id", flat=True), job_ids
        )
        self.assertCountEqual([job.id for job in self.scheduler.get_jobs()], job_ids)

    def test_clear_no_jobs(self) -> None:
        """
        When there are no jobs in the queue, clear_scheduled_jobs does nothing.
        """
        self.assert_jobs(job_ids=[])
        clear_scheduled_jobs(self.scheduler)
        self.assert_jobs(job_ids=[])

    def test_clear_scheduled_jobs(self) -> None:
        """
        Only repeated jobs are removed when clear scheduled jobs is run.
        """
        repeating_job_id = self.add_repeating_job()
        nonrepeating_job_id = self.add_nonrepeating_job()
        self.assert_jobs(job_ids=[repeating_job_id, nonrepeating_job_id])
        clear_scheduled_jobs(self.scheduler)
        self.assert_jobs(job_ids=[nonrepeating_job_id])

    def test_schedule_repeating_job(self) -> None:
        """
        Test that the scheduled_repeating_job method creates the job as expected.
        """
        rqjob = schedule_repeating_job(self.trigger, DummyRepeatingJob, self.scheduler)

        # check RQJob
        self.assertEqual(rqjob.trigger, self.trigger)
        self.assertEqual(rqjob.interval, DummyRepeatingJob.INTERVAL)
        self.assertEqual(rqjob.result_ttl, -1)
        self.assertEqual(rqjob.action_name, DummyRepeatingJob.__name__)

        # check scheduled job
        jobs = [job for job in self.scheduler.get_jobs()]
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.id, rqjob.job_id)
        self.assertEqual(job.meta["interval"], DummyRepeatingJob.INTERVAL)
        self.assertNotIn("repeat", job.meta)
        self.assertEqual(job.meta["action"].__class__, DummyRepeatingJob)
        self.assertEqual(job.meta["template"], self.trigger.template)
        self.assertEqual(job.result_ttl, -1)

    def test_register_scheduled_jobs(self) -> None:
        for action_name in REPEATED_JOBS_BY_TRIGGER.keys():
            Trigger.objects.create(
                action=action_name,
                template=EmailTemplate.objects.create(slug=action_name),
            )
        register_scheduled_jobs(self.scheduler)
        job_actions = [
            job.meta["action"].__class__ for job in self.scheduler.get_jobs()
        ]
        self.assertCountEqual(job_actions, REPEATED_JOBS_BY_TRIGGER.values())
