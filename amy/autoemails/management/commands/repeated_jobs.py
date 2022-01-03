from datetime import datetime
import logging

from django.core.management.base import BaseCommand
import django_rq

from autoemails.actions import BaseRepeatedAction, UpdateProfileReminderRepeatedAction
from autoemails.models import RQJob, Trigger
from autoemails.utils import check_status, scheduled_execution_time

scheduler = django_rq.get_scheduler()
logger = logging.getLogger("amy.signals")
REPEATED_JOBS_BY_TRIGGER = {
    "profile-update": UpdateProfileReminderRepeatedAction,
}
DAY_IN_SECONDS = 86400


def clear_scheduled_jobs():
    # Delete any existing repeated jobs in the scheduler
    for job in scheduler.get_jobs():
        if issubclass(job.meta["action"].__class__, BaseRepeatedAction):
            logger.debug("Deleting scheduled job %s", job)
            job.delete()
            RQJob.objects.filter(job_id=job.get_id()).delete()


def schedule_repeating_job(trigger, action_class: BaseRepeatedAction, _scheduler=None):
    action_name = action_class.__name__
    action = action_class(trigger=trigger)
    meta = dict(
        action=action,
        template=trigger.template,
        email=None,
        context=None,
        email_action_class=action_class.EMAIL_ACTION_CLASS,
    )
    job = _scheduler.schedule(
        scheduled_time=datetime.utcnow(),  # Time for first execution, in UTC timezone
        func=action,  # Function to be queued
        interval=action.INTERVAL,  # Time before the function is called again
        repeat=action.REPEAT,  # Repeat this number of times (None means repeat forever)
        meta=meta,
    )

    scheduled_at = scheduled_execution_time(
        job.get_id(), scheduler=scheduler, naive=False
    )
    logger.debug("%s: job created [%r]", action_name, job)

    # save job ID in the object
    logger.debug(
        "%s: saving job in jobs table",
        action_name,
    )
    rqj = RQJob.objects.create(
        job_id=job.get_id(),
        trigger=trigger,
        scheduled_execution=scheduled_at,
        status=check_status(job),
        mail_status="",
        interval=job.meta.get("interval"),
        result_ttl=job.result_ttl,
        action_name=action_name,
    )
    return rqj


def register_scheduled_jobs():
    triggers = Trigger.objects.filter(
        active=True, action__in=REPEATED_JOBS_BY_TRIGGER.keys()
    )
    for trigger in triggers:
        schedule_repeating_job(
            trigger, REPEATED_JOBS_BY_TRIGGER[trigger.action], scheduler
        )


class Command(BaseCommand):
    """
    Deletes then Re-creates repeated jobs.
    """

    def handle(self, *args, **kwargs):
        clear_scheduled_jobs()  # This is necessary to prevent dupes
        register_scheduled_jobs()
