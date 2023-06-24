from django.conf import settings

from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailLog
from workshops.base_views import AMYDetailView, AMYListView, ConditionallyEnabledMixin
from workshops.utils.access import OnlyForAdminsMixin


class EmailModuleEnabledMixin(ConditionallyEnabledMixin):
    def get_view_enabled(self) -> bool:
        return settings.EMAIL_MODULE_ENABLED is True


class EmailTemplateListView(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYListView):
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_templates"
    template_name = "emails/email_template_list.html"
    queryset = EmailTemplate.objects.order_by("name")
    title = "Email templates"


class EmailTemplateDetailView(
    OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYDetailView
):
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_templates"
    template_name = "emails/email_template_detail.html"
    model = EmailTemplate


class ScheduledEmailListView(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYListView):
    permission_required = ["emails.view_scheduledemail"]
    context_object_name = "scheduled_emails"
    template_name = "emails/scheduled_email_list.html"
    queryset = ScheduledEmail.objects.select_related("template").order_by("-created_at")
    title = "Scheduled emails"


class ScheduledEmailDetailView(
    OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYDetailView
):
    permission_required = ["emails.view_scheduledemail"]
    context_object_name = "scheduled_email"
    template_name = "emails/scheduled_email_detail.html"
    model = ScheduledEmail
    object: ScheduledEmail

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Scheduled email "{self.object.subject}"'
        context["log_entries"] = ScheduledEmailLog.objects.filter(
            scheduled_email=self.object
        ).order_by("-created_at")
        return context
