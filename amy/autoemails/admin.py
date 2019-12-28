from datetime import datetime

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
import django_rq
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq_scheduler.utils import from_unix

from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.utils import scheduled_execution_time
from workshops.util import admin_required


scheduler = django_rq.get_scheduler('default')


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['slug', 'subject', 'to_header', 'from_header']

    def get_urls(self):
        original_urls = super().get_urls()
        new_urls = [
            path(
                'queue/',
                # added `admin_required` for view-access permissions checking
                # test
                admin_required(
                    self.admin_site.admin_view(self.email_queue_view)
                ),
                name='autoemails_emailtemplate_queue',
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
    list_display = ['action', 'active', 'created_at', 'template']


class RQJobAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'created_at', 'scheduled_execution', 'trigger',
                    'manage_links']
    date_hierarchy = 'created_at'

    def manage_links(self, obj):
        link = reverse('admin:autoemails_rqjob_preview', args=[obj.id])
        return format_html('<a href="{}">Preview</a>', link)
    manage_links.short_description = ('Manage')

    def get_urls(self):
        original_urls = super().get_urls()
        new_urls = [
            path(
                '<path:object_id>/preview/',
                admin_required(
                    self.admin_site.admin_view(self.preview)
                ),
                name='autoemails_rqjob_preview',
            ),
            path(
                '<path:object_id>/send_now/',
                admin_required(
                    self.admin_site.admin_view(self.reschedule_now)
                ),
                name='autoemails_rqjob_sendnow',
            ),
        ]
        return new_urls + original_urls

    def preview(self, request, object_id):
        rqjob = RQJob.objects.get(id=object_id)

        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            job_scheduled = scheduled_execution_time(job.get_id(), scheduler)
            instance = job.instance
            trigger = instance.trigger
            template = instance.template
            email = instance._email()
            adn_context = instance.context
        except NoSuchJobError:
            job = None
            job_scheduled = None
            instance = None
            trigger = None
            template = None
            email = None
            adn_context = None

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
        )
        return TemplateResponse(request, "rqjob_preview.html", context)

    def reschedule_now(self, request, object_id):
        """Reschedule an existing job so it executes now (+/- refresh time
        delta, about 1 minute in default settings)."""
        rqjob = RQJob.objects.get(id=object_id)

        link = reverse('admin:autoemails_rqjob_preview', args=[object_id])

        # fetch job
        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            job_scheduled = scheduled_execution_time(job.get_id(), scheduler)
        except NoSuchJobError:
            messages.warning(request, 'The corresponding job in Redis was '
                                      'probably already executed.')
            return redirect(link)

        # new scheduled time: now (in UTC)
        now_utc = datetime.utcnow()

        try:
            scheduler.change_execution_time(job, now_utc)
            messages.info(request,
                          f'The job {rqjob.job_id} was rescheduled to now.')
        except ValueError:
            messages.warning(request, f"The job {rqjob.job_id} was not "
                                      'rescheduled. It is probably already '
                                      'executing or has recently executed.')

        return redirect(link)


admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Trigger, TriggerAdmin)
admin.site.register(RQJob, RQJobAdmin)
