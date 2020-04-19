from datetime import datetime, timedelta
import logging

from django.contrib import admin, messages
from django.db.models import TextField
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST
import django_rq
from markdownx.widgets import AdminMarkdownxWidget
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq_scheduler.utils import from_unix

from autoemails.forms import RescheduleForm
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.utils import scheduled_execution_time
from workshops.util import admin_required


logger = logging.getLogger("amy.signals")
scheduler = django_rq.get_scheduler("default")


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ["slug", "subject", "to_header", "from_header"]
    formfield_overrides = {
        TextField: {"widget": AdminMarkdownxWidget},
    }

    def get_urls(self):
        original_urls = super().get_urls()
        new_urls = [
            path(
                "queue/",
                # added `admin_required` for view-access permissions checking
                # test
                admin_required(self.admin_site.admin_view(self.email_queue_view)),
                name="autoemails_emailtemplate_queue",
            ),
        ]
        return new_urls + original_urls

    def email_queue_view(self, request):
        jobs = list(scheduler.get_jobs(with_times=True))
        context = dict(
            self.admin_site.each_context(request),
            title="Queue",
            cl=self.get_changelist_instance(request),
            queue=jobs,
        )
        return TemplateResponse(request, "queue.html", context)


class TriggerAdmin(admin.ModelAdmin):
    list_display = ["action", "active", "created_at", "template"]


class RQJobAdmin(admin.ModelAdmin):
    list_display = [
        "job_id",
        "manage_links",
        "created_at",
        "scheduled_execution",
        "trigger",
        "status",
        "mail_status",
        "event_slug",
        "recipients",
    ]
    date_hierarchy = "created_at"
    readonly_fields = [
        "scheduled_execution",
        "status",
        "mail_status",
        "event_slug",
        "recipients",
    ]

    def manage_links(self, obj):
        link = reverse("admin:autoemails_rqjob_preview", args=[obj.id])
        return format_html('<b><a href="{}">Preview</a></b>', link)

    manage_links.short_description = "Manage"

    def get_urls(self):
        original_urls = super().get_urls()
        new_urls = [
            path(
                "<path:object_id>/preview/",
                admin_required(self.admin_site.admin_view(self.preview)),
                name="autoemails_rqjob_preview",
            ),
            path(
                "<path:object_id>/reschedule/",
                admin_required(self.admin_site.admin_view(self.reschedule)),
                name="autoemails_rqjob_reschedule",
            ),
            path(
                "<path:object_id>/send_now/",
                admin_required(self.admin_site.admin_view(self.reschedule_now)),
                name="autoemails_rqjob_sendnow",
            ),
            path(
                "<path:object_id>/retry/",
                admin_required(self.admin_site.admin_view(self.retry)),
                name="autoemails_rqjob_retry",
            ),
            path(
                "<path:object_id>/cancel/",
                admin_required(self.admin_site.admin_view(self.cancel)),
                name="autoemails_rqjob_cancel",
            ),
        ]
        return new_urls + original_urls

    def preview(self, request, object_id):
        """Show job + email preview (all details and statuses)."""
        rqjob = get_object_or_404(RQJob, id=object_id)

        logger.debug(f"Previewing job {rqjob.job_id}...")

        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            job_scheduled = scheduled_execution_time(job.get_id(), scheduler)
            instance = job.instance
            logger.debug(f"Job {rqjob.job_id} fetched")

        # the job may not exist anymore, then we can't retrieve any data
        except NoSuchJobError:
            job = None
            job_scheduled = None
            instance = None
            trigger = None
            template = None
            email = None
            adn_context = None
            logger.debug(f"Job {rqjob.job_id} unavailable")

        # we can try and read properties
        else:
            try:
                trigger = instance.trigger
                template = instance.template
                email = instance._email()
                adn_context = instance.context
            except AttributeError:
                trigger = None
                template = None
                email = None
                adn_context = None

        form = None
        if job and not job.is_failed:
            now_utc = datetime.utcnow() + timedelta(minutes=10)
            form = RescheduleForm(
                initial=dict(scheduled_execution=job_scheduled or now_utc)
            )

        # find prev / next RQJob in the list
        previous = RQJob.objects.filter(pk__lt=rqjob.pk).order_by("id").last()
        next_ = RQJob.objects.filter(pk__gt=rqjob.pk).order_by("id").first()

        context = dict(
            self.admin_site.each_context(request),
            cl=self.get_changelist_instance(request),
            title=f"Preview {rqjob}",
            rqjob=rqjob,
            job=job,
            job_scheduled=job_scheduled,
            instance=instance,
            trigger=trigger,
            template=template,
            email=email,
            adn_context=adn_context,
            form=form,
            previous=previous,
            next=next_,
        )
        return TemplateResponse(request, "rqjob_preview.html", context)

    def reschedule(self, request, object_id):
        """Change scheduled execution time to a different timestamp."""
        rqjob = get_object_or_404(RQJob, id=object_id)

        logger.debug(f"Rescheduling job {rqjob.job_id}...")

        link = reverse("admin:autoemails_rqjob_preview", args=[object_id])

        # fetch job
        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            job_scheduled = scheduled_execution_time(job.get_id(), scheduler)
            logger.debug(f"Job {rqjob.job_id} fetched")

        except NoSuchJobError:
            logger.debug(f"Job {rqjob.job_id} unavailable")
            messages.warning(
                request,
                "The corresponding job in Redis was probably already executed.",
            )
            return redirect(link)

        if request.method == "POST":
            form = RescheduleForm(request.POST)
            if form.is_valid():
                new_exec = form.cleaned_data["scheduled_execution"]

                try:
                    scheduler.change_execution_time(job, new_exec)
                    logger.debug(f"Job {rqjob.job_id} rescheduled")
                    messages.info(
                        request,
                        f"The job {rqjob.job_id} was rescheduled to {new_exec}.",
                    )

                except ValueError:
                    logger.debug(f"Job {rqjob.job_id} could not be rescheduled.")
                    messages.warning(
                        request,
                        f"The job {rqjob.job_id} was not "
                        "rescheduled. It is probably already "
                        "executing or has recently executed.",
                    )
            else:
                messages.warning(request, "Please fix errors below.")

        return redirect(link)

    def reschedule_now(self, request, object_id):
        """Reschedule an existing job so it executes now (+/- refresh time
        delta, about 1 minute in default settings)."""
        rqjob = get_object_or_404(RQJob, id=object_id)

        logger.debug(f"Executing job {rqjob.job_id} now (scheduling to +- 1min)...")

        link = reverse("admin:autoemails_rqjob_preview", args=[object_id])

        # fetch job
        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            job_scheduled = scheduled_execution_time(job.get_id(), scheduler)
            logger.debug(f"Job {rqjob.job_id} fetched")

        except NoSuchJobError:
            logger.debug(f"Job {rqjob.job_id} unavailable")
            messages.warning(
                request,
                "The corresponding job in Redis was probably already executed.",
            )
            return redirect(link)

        # new scheduled time: now (in UTC)
        now_utc = datetime.utcnow()

        try:
            scheduler.change_execution_time(job, now_utc)
            logger.debug(f"Job {rqjob.job_id} rescheduled to now")
            messages.info(request, f"The job {rqjob.job_id} was rescheduled to now.")

        except ValueError:
            logger.debug(f"Job {rqjob.job_id} could not be rescheduled.")
            messages.warning(
                request,
                f"The job {rqjob.job_id} was not "
                "rescheduled. It is probably already "
                "executing or has recently executed.",
            )

        return redirect(link)

    def retry(self, request, object_id):
        """Fetch job and re-try to execute it."""
        rqjob = get_object_or_404(RQJob, id=object_id)

        logger.debug(f"Re-trying job {rqjob.job_id}...")

        link = reverse("admin:autoemails_rqjob_preview", args=[object_id])

        # fetch job
        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            logger.debug(f"Job {rqjob.job_id} fetched")

        except NoSuchJobError:
            logger.debug(f"Job {rqjob.job_id} unavailable")
            messages.warning(
                request,
                "The corresponding job in Redis was probably already executed.",
            )
            return redirect(link)

        if job.is_failed:
            job.requeue()
            logger.debug(f"Job {rqjob.job_id} retried. Will run shortly.")
            messages.info(
                request,
                f"The job {rqjob.job_id} was requeued. It will be run shortly.",
            )
        else:
            logger.debug(
                f"Job {rqjob.job_id} can't be retried, because it was successful."
            )
            messages.warning(request, "You cannot re-try a non-failed job.")

        return redirect(link)

    def cancel(self, request, object_id):
        """Fetch job and re-try to execute it."""
        rqjob = get_object_or_404(RQJob, id=object_id)

        logger.debug(f"Cancelling job {rqjob.job_id}...")

        link = reverse("admin:autoemails_rqjob_preview", args=[object_id])

        # fetch job
        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            logger.debug(f"Job {rqjob.job_id} fetched")

        except NoSuchJobError:
            logger.debug(f"Job {rqjob.job_id} unavailable")
            messages.warning(
                request,
                "The corresponding job in Redis was probably already executed.",
            )
            return redirect(link)

        if job.is_queued or not job.get_status():
            job.cancel()  # for "pure" jobs
            scheduler.cancel(job)  # for scheduler-based jobs

            logger.debug(f"Job {rqjob.job_id} was cancelled.")
            messages.info(request, f"The job {rqjob.job_id} was cancelled.")

        elif job.is_started:
            # Right now we don't know how to test a started job, so we simply
            # don't allow such jobs to be cancelled.
            logger.debug(f"Job {rqjob.job_id} has started and cannot be cancelled.")
            messages.warning(
                request, f"Job {rqjob.job_id} has started and cannot be cancelled."
            )

        elif job.get_status() not in ("", None):
            logger.debug(
                f"Job {rqjob.job_id} has unknown status or was already executed."
            )
            messages.warning(request, "Job has unknown status or was already executed.")

        return redirect(link)


admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Trigger, TriggerAdmin)
admin.site.register(RQJob, RQJobAdmin)
