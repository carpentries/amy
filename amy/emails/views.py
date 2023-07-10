from typing import Any

from django.conf import settings
from django.shortcuts import get_object_or_404

from emails.controller import EmailController
from emails.forms import (
    ScheduledEmailCancelForm,
    ScheduledEmailEditForm,
    ScheduledEmailRescheduleForm,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailLog
from workshops.base_views import (
    AMYDetailView,
    AMYFormView,
    AMYListView,
    AMYUpdateView,
    ConditionallyEnabledMixin,
)
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
    context_object_name = "email_template"
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


class ScheduledEmailEditView(
    OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYUpdateView
):
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    context_object_name = "scheduled_email"
    template_name = "emails/scheduled_email_edit.html"
    form_class = ScheduledEmailEditForm
    model = ScheduledEmail
    object: ScheduledEmail

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Scheduled email "{self.object.subject}"'
        return context


class ScheduledEmailRescheduleView(
    OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYFormView
):
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    template_name = "emails/scheduled_email_reschedule.html"
    form_class = ScheduledEmailRescheduleForm
    object: ScheduledEmail
    title: str

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(ScheduledEmail, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        self.title = f'Scheduled email "{self.object.subject}"'
        kwargs["scheduled_email"] = self.object
        return super().get_context_data(**kwargs)

    def get_initial(self) -> dict[str, Any]:
        return {
            "scheduled_at": self.object.scheduled_at,
        }

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()

    def form_valid(self, form: ScheduledEmailRescheduleForm):
        EmailController.reschedule_email(self.object, form.cleaned_data["scheduled_at"])
        return super().form_valid(form)


class ScheduledEmailCancelView(
    OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYFormView
):
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    template_name = "emails/scheduled_email_cancel.html"
    form_class = ScheduledEmailCancelForm
    object: ScheduledEmail
    title: str

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(ScheduledEmail, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        self.title = f'Scheduled email "{self.object.subject}"'
        kwargs["scheduled_email"] = self.object
        return super().get_context_data(**kwargs)

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()

    def form_valid(self, form: ScheduledEmailRescheduleForm):
        if form.cleaned_data.get("confirm"):
            EmailController.cancel_email(self.object)

        return super().form_valid(form)
