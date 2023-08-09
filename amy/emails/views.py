from typing import Any, cast

from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from flags.views import FlaggedViewMixin
from django.views.generic.detail import SingleObjectMixin
from markdownx.utils import markdownify

from emails.controller import EmailController
from emails.forms import (
    EmailTemplateCreateForm,
    EmailTemplateUpdateForm,
    ScheduledEmailCancelForm,
    ScheduledEmailRescheduleForm,
    ScheduledEmailUpdateForm,
)
from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
    ScheduledEmailStatusActions,
    ScheduledEmailStatusExplanation,
)
from emails.signals import ALL_SIGNALS
from emails.utils import find_signal_by_name, person_from_request
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYFormView,
    AMYListView,
    AMYUpdateView,
)
from workshops.utils.access import OnlyForAdminsMixin


class AllEmailTemplates(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_templates"
    template_name = "emails/email_template_list.html"
    queryset = EmailTemplate.objects.order_by("name")
    title = "Email templates"


class EmailTemplateDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_template"
    template_name = "emails/email_template_detail.html"
    model = EmailTemplate
    object: EmailTemplate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Email template "{self.object}"'
        context["rendered_body"] = markdownify(self.object.body)

        signal = find_signal_by_name(self.object.signal, ALL_SIGNALS)

        context["body_context_type"] = None
        context["body_context_annotations"] = {}
        if signal:
            context["body_context_type"] = signal.context_type
            context["body_context_annotations"] = signal.context_type.__annotations__
        return context


class EmailTemplateCreate(OnlyForAdminsMixin, FlaggedViewMixin, AMYCreateView):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.add_emailtemplate"]
    template_name = "emails/email_template_create.html"
    form_class = EmailTemplateCreateForm
    model = EmailTemplate
    object: EmailTemplate
    title = "Create a new email template"


class EmailTemplateUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_emailtemplate", "emails.change_emailtemplate"]
    context_object_name = "email_template"
    template_name = "emails/email_template_edit.html"
    form_class = EmailTemplateUpdateForm
    model = EmailTemplate
    object: EmailTemplate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f'Email template "{self.object}"'

        signal = find_signal_by_name(self.object.signal, ALL_SIGNALS)

        context["body_context_type"] = None
        context["body_context_annotations"] = {}
        if signal:
            context["body_context_type"] = signal.context_type
            context["body_context_annotations"] = signal.context_type.__annotations__
        return context


class EmailTemplateDelete(OnlyForAdminsMixin, FlaggedViewMixin, AMYDeleteView):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.delete_emailtemplate"]
    model = EmailTemplate

    def get_success_url(self) -> str:
        return reverse("all_emailtemplates")


# -------------------------------------------------------------------------------


class AllScheduledEmails(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_scheduledemail"]
    context_object_name = "scheduled_emails"
    template_name = "emails/scheduled_email_list.html"
    queryset = ScheduledEmail.objects.select_related("template").order_by("-created_at")
    title = "Scheduled emails"


class ScheduledEmailDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView):
    flag_name = "EMAIL_MODULE"
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

        context["status_explanation"] = ScheduledEmailStatusExplanation[
            ScheduledEmailStatus(self.object.state)
        ]
        context["ScheduledEmailStatusActions"] = ScheduledEmailStatusActions
        return context


class ScheduledEmailUpdate(OnlyForAdminsMixin, FlaggedViewMixin, AMYUpdateView):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    context_object_name = "scheduled_email"
    template_name = "emails/scheduled_email_edit.html"
    form_class = ScheduledEmailUpdateForm
    model = ScheduledEmail
    object: ScheduledEmail

    # Will lock this object in the database for the duration of the request.
    # Most specifically, we want to lock it when we're saving the form. This way the DB
    # helps us make sure the data is consistent.
    # Additionally, we're limiting the queryset to only those objects that can be edited
    # (see ScheduledEmailStatusActions).
    queryset = ScheduledEmail.objects.filter(
        state__in=ScheduledEmailStatusActions["edit"]
    ).select_for_update()

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
    OnlyForAdminsMixin, FlaggedViewMixin, SingleObjectMixin, AMYFormView
):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    template_name = "emails/scheduled_email_reschedule.html"
    form_class = ScheduledEmailRescheduleForm
    object: ScheduledEmail
    request: HttpRequest
    title: str

    # Will lock this object in the database for the duration of the request.
    # Most specifically, we want to lock it when we're saving the form. This way the DB
    # helps us make sure the data is consistent.
    # Additionally, we're limiting the queryset to only those objects that can be edited
    # (see ScheduledEmailStatusActions).
    queryset = ScheduledEmail.objects.filter(
        state__in=ScheduledEmailStatusActions["reschedule"]
    ).select_for_update()

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        self.request = request
        self.object = cast(ScheduledEmail, self.get_object())
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


class ScheduledEmailCancel(
    OnlyForAdminsMixin, FlaggedViewMixin, SingleObjectMixin, AMYFormView
):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail"]
    template_name = "emails/scheduled_email_cancel.html"
    form_class = ScheduledEmailCancelForm
    object: ScheduledEmail
    request: HttpRequest
    title: str

    # Will lock this object in the database for the duration of the request.
    # Most specifically, we want to lock it when we're saving the form. This way the DB
    # helps us make sure the data is consistent.
    # Additionally, we're limiting the queryset to only those objects that can be edited
    # (see ScheduledEmailStatusActions).
    queryset = ScheduledEmail.objects.filter(
        state__in=ScheduledEmailStatusActions["cancel"]
    ).select_for_update()

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        self.request = request
        self.object = cast(ScheduledEmail, self.get_object())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        self.title = f'Scheduled email "{self.object.subject}"'
        kwargs["scheduled_email"] = self.object
        return super().get_context_data(**kwargs)

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()

    def form_valid(self, form: ScheduledEmailCancelForm):
        if form.cleaned_data.get("confirm"):
            EmailController.cancel_email(
                self.object,
                author=person_from_request(self.request),
            )

        return super().form_valid(form)
