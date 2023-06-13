from emails.models import EmailTemplate, ScheduledEmail
from workshops.base_views import AMYListView
from workshops.utils.access import OnlyForAdminsMixin


class EmailTemplateListView(OnlyForAdminsMixin, AMYListView):
    context_object_name = "email_templates"
    template_name = "emails/email_template_list.html"
    queryset = EmailTemplate.objects.order_by("name")
    title = "Email Templates"


class ScheduledEmailListView(OnlyForAdminsMixin, AMYListView):
    context_object_name = "scheduled_emails"
    template_name = "emails/scheduled_email_list.html"
    queryset = ScheduledEmail.objects.select_related("template").order_by("-created_at")
    title = "Scheduled Emails"
