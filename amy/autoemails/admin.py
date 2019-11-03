from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

import django_rq

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
    list_display = ['active', 'created_at', 'action', 'template']


class RQJobAdmin(admin.ModelAdmin):
    list_display = ['job_id', ]


admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Trigger, TriggerAdmin)
admin.site.register(RQJob, RQJobAdmin)
