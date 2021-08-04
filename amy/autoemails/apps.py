import datetime

from django.apps import AppConfig
import django_rq


class AutoemailsConfig(AppConfig):
    name = "autoemails"

    def ready(self):
        from amy.autoemails.utils import schedule_repeated_jobs
        from autoemails.actions import ProfileArchivalWarningAction

        scheduler = django_rq.get_scheduler("default")

        # Delete any existing jobs in the scheduler when the app starts up
        jobs = scheduler.get_jobs()
        for job in jobs:
            if isinstance(job, ProfileArchivalWarningAction):
                breakpoint()
                job.delete()

        # Have 'mytask' run every 5 minutes
        # scheduler.schedule(datetime.utcnow(), 'mytask', interval=60*5)
        schedule_repeated_jobs(scheduler)
