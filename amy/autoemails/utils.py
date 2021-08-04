from datetime import datetime
import logging
from typing import Union

import django_rq
import pytz
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq_scheduler.utils import from_unix

from autoemails.models import Trigger

logger = logging.getLogger("amy.signals")


def scheduled_execution_time(job_id, scheduler=None, naive=True):
    """Get RQ-Scheduler scheduled execution time for specific job."""
    _scheduler = scheduler
    if not scheduler:
        _scheduler = django_rq.get_scheduler("default")

    # Scheduler keeps jobs in a single key, they are sorted by score, which is
    # scheduled execution time (linux epoch).  We can retrieve single
    # entry's score.
    time = _scheduler.connection.zscore(_scheduler.scheduled_jobs_key, job_id)

    # Convert linux time epoch to UTC.
    if time:
        time = from_unix(time)
        if not naive:
            # By default, RQ-Scheduler uses UTC naive (TZ-unaware) objects,
            # which we can "convert" to TZ-aware UTC.
            time = time.replace(tzinfo=pytz.UTC)
    return time


def compare_emails(a, b):
    """EmailMultiAlternatives doesn't implement __eq__, so we have to
    cheat our way."""
    if a is None and b is None:
        return True
    elif a is None and b or b is None and a:
        return False
    else:
        try:
            return (
                a.to == b.to
                and a.cc == b.cc
                and a.bcc == b.bcc
                and a.reply_to == b.reply_to
                and a.subject == b.subject
                and a.body == b.body
            )
        except AttributeError:
            return False


def check_status(job: Union[str, Job], scheduler=None):
    _scheduler = scheduler
    if not scheduler:
        _scheduler = django_rq.get_scheduler("default")

    if not isinstance(job, Job):
        try:
            job = Job.fetch(job, connection=_scheduler.connection)
        except NoSuchJobError:
            return None

    scheduled = scheduled_execution_time(job.get_id(), scheduler)

    if scheduled:
        return job.get_status() or "scheduled"
    else:
        return job.get_status() or "cancelled"


def schedule_repeated_jobs(scheduler=None):
    from autoemails.actions import ProfileArchivalWarningAction
    from consents.models import Term

    _scheduler = scheduler
    if not scheduler:
        _scheduler = django_rq.get_scheduler("default")
    breakpoint()
    list_of_job_instances = list(scheduler.get_jobs())
    triggers = Trigger.objects.filter(active=True, action="archive-warning")
    for trigger in triggers:
        action_name = ProfileArchivalWarningAction.__name__
        action = ProfileArchivalWarningAction(
            trigger=trigger,
            objects=dict(),
        )
        # TODO: this doesn't make sense
        object_ = Term.objects.active()[0]
        launch_at = action.get_launch_at()
        meta = dict(
            action=action,
            template=trigger.template,
            launch_at=launch_at,
            email=None,
            context=None,
        )
        job = _scheduler.schedule(
            scheduled_time=datetime.utcnow()
            + launch_at,  # Time for first execution, in UTC timezone
            func=action,  # Function to be queued
            interval=86400,  # Time before the function is called again, 1 day in seconds
            repeat=None,
            meta=meta,  # Repeat this number of times (None means repeat forever)
        )

        scheduled_at = scheduled_execution_time(
            job.get_id(), scheduler=scheduler, naive=False
        )
        logger.debug("%s: job created [%r]", action_name, job)

        # save job ID in the object
        logger.debug("%s: saving job in [%r] object", action_name, object_)
        rqj = object_.rq_jobs.create(
            job_id=job.get_id(),
            trigger=trigger,
            scheduled_execution=scheduled_at,
            status=check_status(job),
            mail_status="",
            interval=job.meta.get("interval"),
            result_ttl=job.result_ttl,
            # event_slug=action.event_slug(),
            # recipients=action.all_recipients(),
        )
    list_of_job_instances = list(scheduler.get_jobs())
