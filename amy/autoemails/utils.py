from typing import Union

import django_rq
import pytz
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq_scheduler.utils import from_unix


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
