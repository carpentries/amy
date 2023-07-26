from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from markdownx.utils import markdownify

from emails.controller import EmailController
from emails.forms import (
    EmailTemplateCreateForm,
    EmailTemplateUpdateForm,
    ScheduledEmailCancelForm,
    ScheduledEmailRescheduleForm,
    ScheduledEmailUpdateForm,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailLog
from emails.signals import ALL_SIGNALS
from emails.utils import person_from_request
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
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


class AllEmailTemplates(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYListView):
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_templates"
    template_name = "emails/email_template_list.html"
    queryset = EmailTemplate.objects.order_by("name")
    title = "Email templates"


class EmailTemplateDetails(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYDetailView):
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_template"
    template_name = "emails/email_template_detail.html"
    model = EmailTemplate
    object: EmailTemplate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Email template "{self.object}"'
        context["rendered_body"] = markdownify(self.object.body)

        signal = next(
            (
                signal
                for signal in ALL_SIGNALS
                if signal.signal_name == self.object.signal
            ),
            None,
        )
        context["body_context_type"] = signal.context_type if signal else {}
        context["body_context_annotations"] = context[
            "body_context_type"
        ].__annotations__
        return context


class EmailTemplateCreate(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYCreateView):
    permission_required = ["emails.add_emailtemplate"]
    template_name = "emails/email_template_create.html"
    form_class = EmailTemplateCreateForm
    model = EmailTemplate
    object: EmailTemplate
    title = "Create a new email template"


class EmailTemplateUpdate(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYUpdateView):
    permission_required = ["emails.view_emailtemplate", "emails.change_emailtemplate"]
    context_object_name = "email_template"
    template_name = "emails/email_template_edit.html"
    form_class = EmailTemplateUpdateForm
    model = EmailTemplate
    object: EmailTemplate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Email template "{self.object}"'
        return context


class EmailTemplateDelete(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYDeleteView):
    permission_required = ["emails.delete_emailtemplate"]
    model = EmailTemplate

    def get_success_url(self) -> str:
        return reverse("all_emailtemplates")


# -------------------------------------------------------------------------------


class AllScheduledEmails(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYListView):
    permission_required = ["emails.view_scheduledemail"]
    context_object_name = "scheduled_emails"
    template_name = "emails/scheduled_email_list.html"
    queryset = ScheduledEmail.objects.select_related("template").order_by("-created_at")
    title = "Scheduled emails"


class ScheduledEmailDetails(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYDetailView):
    permission_required = ["emails.view_scheduledemail"]
    context_object_name = "scheduled_email"
    template_name = "emails/scheduled_email_detail.html"
    model = ScheduledEmail
    object: ScheduledEmail

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Scheduled email "{self.object.subject}"'
        context["log_entries"] = (
            ScheduledEmailLog.objects.select_related("author")
            .filter(scheduled_email=self.object)
            .order_by("-created_at")
        )
        context["rendered_body"] = markdownify(self.object.body)

        signal = next(
            (
                signal
                for signal in ALL_SIGNALS
                if self.object.template
                and signal.signal_name == self.object.template.signal
            ),
            None,
        )
        context["body_context_type"] = signal.context_type if signal else {}
        context["body_context_annotations"] = context[
            "body_context_type"
        ].__annotations__
        return context


class ScheduledEmailUpdate(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYUpdateView):
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    context_object_name = "scheduled_email"
    template_name = "emails/scheduled_email_edit.html"
    form_class = ScheduledEmailUpdateForm
    model = ScheduledEmail
    object: ScheduledEmail

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Scheduled email "{self.object.subject}"'
        return context

    def form_valid(self, form: ScheduledEmailUpdateForm) -> HttpResponse:
        result = super().form_valid(form)

        ScheduledEmailLog.objects.create(
            details="Scheduled email was changed.",
            state_before=self.object.state,
            state_after=self.object.state,
            scheduled_email=self.object,
            author=person_from_request(self.request),
        )

        return result


class ScheduledEmailReschedule(
    OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYFormView
):
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    template_name = "emails/scheduled_email_reschedule.html"
    form_class = ScheduledEmailRescheduleForm
    object: ScheduledEmail
    request: HttpRequest
    title: str

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        self.request = request
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

    def form_valid(self, form: ScheduledEmailRescheduleForm) -> HttpResponse:
        EmailController.reschedule_email(
            self.object,
            form.cleaned_data["scheduled_at"],
            author=person_from_request(self.request),
        )
        return super().form_valid(form)


class ScheduledEmailCancel(OnlyForAdminsMixin, EmailModuleEnabledMixin, AMYFormView):
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    template_name = "emails/scheduled_email_cancel.html"
    form_class = ScheduledEmailCancelForm
    object: ScheduledEmail
    request: HttpRequest
    title: str

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        self.request = request
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
            EmailController.cancel_email(
                self.object,
                author=person_from_request(self.request),
            )

        return super().form_valid(form)
