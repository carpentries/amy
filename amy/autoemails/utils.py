import django_rq
import pytz
from rq_scheduler.utils import from_unix


def scheduled_execution_time(job_id, scheduler=None, naive=True):
    """Get RQ-Scheduler scheduled execution time for specific job."""
    _scheduler = scheduler
    if not scheduler:
        _scheduler = django_rq.get_scheduler('default')

    # Scheduler keeps jobs in a single key, they are sorted by score, which is
    # scheduled execution time (linux epoch).  We can retrieve single
    # entry's score.
    time = _scheduler.connection.zscore(
        _scheduler.scheduled_jobs_key, job_id
    )

    # Convert linux time epoch to UTC.
    if time:
        time = from_unix(time)
        if not naive:
            # By default, RQ-Scheduler uses UTC naive (TZ-unaware) objects,
            # which we can "convert" to TZ-aware UTC.
            time = time.replace(tzinfo=pytz.UTC)
    return time
