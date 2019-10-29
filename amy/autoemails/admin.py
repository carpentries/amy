from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

import django_rq

from .models import EmailTemplate, Trigger


scheduler = django_rq.get_scheduler('default')


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['slug', 'subject', 'to_header', 'from_header']

    def get_urls(self):
        original_urls = super().get_urls()
        new_urls = [
            path('queue/', self.admin_site.admin_view(self.email_queue_view),
                 name='autoemails_emailtemplate_queue'),
        ]
        return new_urls + original_urls

    def email_queue_view(self, request):
        jobs = scheduler.get_jobs()
        context = dict(
            self.admin_site.each_context(request),
            title="Queue",
            cl=self.get_changelist_instance(request),
            queue=jobs,
        )
        return TemplateResponse(request, "queue.html", context)


class TriggerAdmin(admin.ModelAdmin):
    list_display = ['active', 'created_at', 'action', 'template']


admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Trigger, TriggerAdmin)
