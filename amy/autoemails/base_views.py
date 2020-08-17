from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from rq.exceptions import NoSuchJobError

from autoemails.job import Job
from autoemails.utils import (
    check_status,
    scheduled_execution_time,
)


class ActionManageMixin:
    """Mixin used for adding/removing Actions related to an object.
    """

    def get_logger(self):
        raise NotImplementedError()

    def get_scheduler(self):
        raise NotImplementedError()

    def get_redis_connection(self):
        raise NotImplementedError()

    def get_triggers(self):
        raise NotImplementedError()

    def get_jobs(self, as_id_list=False):
        raise NotImplementedError()

    def objects(self):
        raise NotImplementedError()

    @staticmethod
    def add(
        action_class,
        logger,
        scheduler,
        triggers,
        context_objects,
        object_,
        request=None,
    ):
        Action = action_class
        action_name = Action.__name__

        logger.debug("%s: adding jobs...", action_name)

        # fetch all related triggers
        logger.debug("%s: found %d triggers", action_name, triggers.count())

        created_jobs = []
        created_rqjobs = []

        for trigger in triggers:
            # create action
            logger.debug("%s: creating an action object", action_name)
            action = Action(trigger=trigger, objects=dict(context_objects))

            # prepare launch timestamp and some metadata
            launch_at = action.get_launch_at()
            meta = dict(
                action=action,
                template=trigger.template,
                launch_at=launch_at,
                email=None,
                context=None,
            )

            # enqueue job at specified timestamp with metadata
            logger.debug("%s: enqueueing", action_name)
            job = scheduler.enqueue_in(launch_at, action, meta=meta)
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
                event_slug=action.event_slug(),
                recipients=action.all_recipients(),
            )

            created_jobs.append(job)
            created_rqjobs.append(rqj)

            # `request` is optionally passed down from the view
            if request:
                messages.info(
                    request,
                    format_html(
                        'New email ({}) was scheduled to run '
                        '<relative-time datetime="{}">{}</relative-time>: '
                        '<a href="{}">{}</a>.',
                        trigger.get_action_display(),
                        scheduled_at.isoformat(),
                        '{:%Y-%m-%d %H:%M}'.format(scheduled_at),
                        reverse("admin:autoemails_rqjob_preview", args=[rqj.pk]),
                        job.id,
                    ),
                    fail_silently=True,
                )

        return created_jobs, created_rqjobs

    @staticmethod
    def remove(
        action_class, logger, scheduler, connection, jobs, object_, request=None,
    ):
        Action = action_class
        action_name = Action.__name__

        logger.debug("%s: removing jobs...", action_name)

        # fetch all related jobs
        if not jobs:
            logger.debug("%s: no existing jobs available", action_name)

        else:
            logger.debug("%s: found %d existing jobs in DB", action_name, jobs.count())

            # turn into a list, just in case
            jobs = list(jobs)

            # cancel enqueued or scheduled jobs
            for job in jobs:
                # Try remove (cancel) a scheduled job in RQ-Scheduler.  Behind
                # the curtains, it accesses Redis' `zrem`, which ignores
                # non-existing members of a set.
                if scheduler.connection.zscore(scheduler.scheduled_jobs_key, job):
                    scheduler.cancel(job)
                    logger.debug("%s: scheduled job [%r] deleted", action_name, job)

                try:
                    # fetch job from Reddit - if only it's already enqueued
                    enqueued_job = Job.fetch(job, connection=connection)
                    # we don't need to check if job is finished or failed, we
                    # can blindly delete it
                    enqueued_job.delete(remove_from_queue=True)
                    logger.debug("%s: enqueued job [%r] deleted", action_name, job)

                except NoSuchJobError:
                    pass

                # add message about removing the job
                if request:
                    messages.info(
                        request,
                        format_html(
                            "Scheduled email {} was removed because action "
                            "conditions have changed. "
                            '<a href="{}">See other scheduled jobs</a>.',
                            job,
                            reverse("admin:autoemails_rqjob_changelist"),
                        ),
                        fail_silently=True,
                    )

            # remove DB job objects
            object_.rq_jobs.filter(job_id__in=jobs).delete()
            logger.debug("%s: jobs removed from %r", action_name, object_)

    def action_add(self, action_class):
        return ActionManageMixin.add(
            action_class=action_class,
            logger=self.get_logger(),
            scheduler=self.get_scheduler(),
            triggers=self.get_triggers(),
            context_objects=self.objects(),
            object_=self.object,
            request=self.request,
        )

    def action_remove(self, action_class):
        return ActionManageMixin.remove(
            action_class=action_class,
            logger=self.get_logger(),
            scheduler=self.get_scheduler(),
            connection=self.get_redis_connection(),
            jobs=self.get_jobs(as_id_list=True),
            object_=self.object,
            request=self.request,
        )
