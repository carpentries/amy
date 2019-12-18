import django_rq
from rq_scheduler.utils import from_unix


def scheduled_execution_time(job_id, scheduler=None):
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
    return time
