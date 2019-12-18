from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
import django_rq
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq_scheduler.utils import from_unix

from autoemails.models import EmailTemplate, Trigger, RQJob
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
        ]
        return new_urls + original_urls

    def preview(self, request, object_id):
        rqjob = RQJob.objects.get(id=object_id)

        try:
            job = Job.fetch(rqjob.job_id, connection=scheduler.connection)
            job_scheduled = scheduler.connection.zscore(
                scheduler.scheduled_jobs_key, job.get_id()
            )
            if job_scheduled:
                job_scheduled = from_unix(job_scheduled)
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


admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Trigger, TriggerAdmin)
admin.site.register(RQJob, RQJobAdmin)
