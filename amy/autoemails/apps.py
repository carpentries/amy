from django.apps import AppConfig
import django_rq
import datetime

class AutoemailsConfig(AppConfig):
    name = "autoemails"

    def ready(self):
        from autoemails.actions import ProfileArchivalWarningAction
        from amy.autoemails.utils import schedule_repeated_jobs
        scheduler = django_rq.get_scheduler('default')

        # Delete any existing jobs in the scheduler when the app starts up
        jobs = scheduler.get_jobs()
        for job in jobs:
            if isinstance(job, ProfileArchivalWarningAction):
                breakpoint()
                job.delete()

        # Have 'mytask' run every 5 minutes
        # scheduler.schedule(datetime.utcnow(), 'mytask', interval=60*5)
        schedule_repeated_jobs(scheduler)
