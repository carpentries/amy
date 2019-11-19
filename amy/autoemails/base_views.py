from django.contrib import messages
from django.urls import reverse
from rq.exceptions import NoSuchJobError
from rq.job import Job


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

    def action_add(self, action_class):
        Action = action_class
        action_name = Action.__name__

        logger = self.get_logger()
        logger.debug('%s: adding jobs...', action_name)

        # fetch all related triggers
        triggers = self.get_triggers()
        logger.debug('%s: found %d triggers',
                     action_name,
                     triggers.count())

        for trigger in triggers:
            # create action
            logger.debug('%s: creating an action object', action_name)
            action = Action(trigger=trigger, objects=dict(self.objects()))

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
            logger.debug('%s: enqueueing', action_name)
            job = self.get_scheduler().enqueue_in(launch_at, action,
                                                  meta=meta)
            logger.debug('%s: job created [%r]', action_name, job)

            # save job ID in the object
            logger.debug('%s: saving job in [%r] object', action_name,
                         self.object)
            self.object.rq_jobs.create(job_id=job.get_id(), trigger=trigger)

            # both `self.object` and `self.request` are made available by
            # other mixins
            messages.info(
                self.request,
                'New email was scheduled: <a href="{}">{}</a>.'.format(
                    reverse('admin:autoemails_rqjob_changelist'),
                    job.id,
                ),
                fail_silently=True,
            )

    def action_remove(self, action_class):
        Action = action_class
        action_name = Action.__name__

        logger = self.get_logger()
        logger.debug('%s: removing jobs...', action_name)

        # fetch all related jobs
        job_ids = self.get_jobs(as_id_list=True)
        if not job_ids:
            logger.debug('%s: no existing jobs available', action_name)

        else:
            logger.debug('%s: found %d existing jobs in DB',
                         action_name,
                         job_ids.count())

            job_ids = list(job_ids)

            scheduler = self.get_scheduler()
            connection = self.get_redis_connection()

            # cancel enqueued or scheduled jobs
            for job in job_ids:
                try:
                    # fetch job from Reddit - if only it's already enqueued
                    enqueued_job = Job.fetch(job, connection=connection)
                    # we don't need to check if job is finished or failed, we
                    # can blindly delete it
                    enqueued_job.delete(remove_from_queue=True)
                    logger.debug('%s: enqueued job [%r] deleted', action_name,
                                 job)

                except NoSuchJobError:
                    # apparently the job is not enqueued yet, let's cancel
                    # it from the scheduler interface
                    scheduler.cancel(job)
                    logger.debug('%s: scheduled job [%r] deleted', action_name,
                                 job)

                # add message about removing the job
                messages.info(
                    self.request,
                    'Scheduled email was removed because action conditions '
                    'have changed: {}'.format(job),
                    fail_silently=True,
                )

            # remove DB job objects
            self.object.rq_jobs.filter(job_id__in=job_ids).delete()
            logger.debug('%s: jobs removed from %r', action_name, self.object)
