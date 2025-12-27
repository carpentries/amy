from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.urls import reverse
from django.views.generic.detail import SingleObjectMixin
from flags.views import FlaggedViewMixin  # type: ignore[import-untyped]
from jinja2 import DebugUndefined, Environment, TemplateError
from markdownx.utils import markdownify

from src.emails.controller import EmailController
from src.emails.filters import EmailTemplateFilter, ScheduledEmailFilter
from src.emails.forms import (
    EmailTemplateCreateForm,
    EmailTemplateUpdateForm,
    ScheduledEmailAddAttachmentForm,
    ScheduledEmailCancelForm,
    ScheduledEmailRescheduleForm,
    ScheduledEmailUpdateForm,
)
from src.emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
    ScheduledEmailStatusActions,
    ScheduledEmailStatusExplanation,
)
from src.emails.signals import ALL_SIGNALS
from src.emails.utils import (
    build_context_from_dict,
    build_context_from_list,
    find_signal_by_name,
    jinjanify,
    person_from_request,
)
from src.workshops.base_forms import GenericDeleteForm
from src.workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYFormView,
    AMYListView,
    AMYUpdateView,
)
from src.workshops.utils.access import OnlyForAdminsMixin


class AllEmailTemplates(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[EmailTemplate]):  # type: ignore[misc]
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_templates"
    template_name = "emails/email_template_list.html"
    queryset = EmailTemplate.objects.order_by("name")
    title = "Email templates"
    filter_class = EmailTemplateFilter


class EmailTemplateDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[EmailTemplate]):  # type: ignore[misc]
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_emailtemplate"]
    context_object_name = "email_template"
    template_name = "emails/email_template_detail.html"
    model = EmailTemplate

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f'Email template "{self.object}"'
        context["rendered_body"] = markdownify(self.object.body)  # type: ignore

        signal = find_signal_by_name(self.object.signal, ALL_SIGNALS)

        context["body_context_type"] = None
        context["body_context_annotations"] = {}
        if signal:
            context["body_context_type"] = signal.context_type
            context["body_context_annotations"] = {k: repr(v) for k, v in signal.context_type.__annotations__.items()}
        return context


class EmailTemplateCreate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYCreateView[EmailTemplateCreateForm, EmailTemplate],
):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.add_emailtemplate"]
    template_name = "emails/email_template_create.html"
    form_class = EmailTemplateCreateForm
    model = EmailTemplate
    object: EmailTemplate
    title = "Create a new email template"


class EmailTemplateUpdate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYUpdateView[EmailTemplateCreateForm, EmailTemplate],
):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_emailtemplate", "emails.change_emailtemplate"]
    context_object_name = "email_template"
    template_name = "emails/email_template_edit.html"
    form_class = EmailTemplateUpdateForm
    model = EmailTemplate
    object: EmailTemplate

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f'Email template "{self.object}"'

        signal = find_signal_by_name(self.object.signal, ALL_SIGNALS)

        context["body_context_type"] = None
        context["body_context_annotations"] = {}
        if signal:
            context["body_context_type"] = signal.context_type
            context["body_context_annotations"] = {k: repr(v) for k, v in signal.context_type.__annotations__.items()}
        return context


class EmailTemplateDelete(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYDeleteView[EmailTemplate, GenericDeleteForm[EmailTemplate]],
):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.delete_emailtemplate"]
    model = EmailTemplate

    def get_success_url(self) -> str:
        return reverse("all_emailtemplates")


# -------------------------------------------------------------------------------


class AllScheduledEmails(OnlyForAdminsMixin, FlaggedViewMixin, AMYListView[ScheduledEmail]):  # type: ignore[misc]
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_scheduledemail"]
    context_object_name = "scheduled_emails"
    template_name = "emails/scheduled_email_list.html"
    queryset = ScheduledEmail.objects.select_related("template").order_by("-created_at")
    title = "Scheduled emails"
    filter_class = ScheduledEmailFilter


class ScheduledEmailDetails(OnlyForAdminsMixin, FlaggedViewMixin, AMYDetailView[ScheduledEmail]):  # type: ignore[misc]
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_scheduledemail"]
    context_object_name = "scheduled_email"
    template_name = "emails/scheduled_email_detail.html"
    model = ScheduledEmail
    object: ScheduledEmail

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f'Scheduled email "{self.object.subject}"'
        context["log_entries"] = (
            ScheduledEmailLog.objects.select_related("author")
            .filter(scheduled_email=self.object)
            .order_by("-created_at")
        )[0:500]

        engine = Environment(autoescape=True, undefined=DebugUndefined)
        try:
            body_context = build_context_from_dict(self.object.context_json)
            context["rendered_context"] = body_context
        except ValueError as exc:
            body_context = {}
            context["rendered_context"] = f"Unable to render context: {exc}"

        try:
            context["rendered_body"] = markdownify(jinjanify(engine, self.object.body, body_context))  # type: ignore
        except (TemplateError, AttributeError, ValueError, TypeError) as exc:
            context["rendered_body"] = markdownify(f"Unable to render template: {exc}")  # type: ignore

        try:
            context["rendered_subject"] = jinjanify(engine, self.object.subject, body_context)
        except (TemplateError, AttributeError, ValueError, TypeError) as exc:
            context["rendered_subject"] = f"Unable to render template: {exc}"

        try:
            to_header_context = build_context_from_list(self.object.to_header_context_json)
            context["rendered_to_header_context"] = to_header_context
        except ValueError as exc:
            context["rendered_to_header_context"] = f"Unable to render context: {exc}"

        context["status_explanation"] = ScheduledEmailStatusExplanation[ScheduledEmailStatus(self.object.state)]
        context["ScheduledEmailStatusActions"] = ScheduledEmailStatusActions
        return context


class ScheduledEmailUpdate(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    AMYUpdateView[ScheduledEmailUpdateForm, ScheduledEmail],
):
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
    queryset = ScheduledEmail.objects.filter(state__in=ScheduledEmailStatusActions["edit"]).select_for_update()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
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
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    SingleObjectMixin[ScheduledEmail],
    AMYFormView[ScheduledEmailRescheduleForm],
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
    queryset = ScheduledEmail.objects.filter(state__in=ScheduledEmailStatusActions["reschedule"]).select_for_update()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.request = request
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
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
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    SingleObjectMixin[ScheduledEmail],
    AMYFormView[ScheduledEmailCancelForm],
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
    queryset = ScheduledEmail.objects.filter(state__in=ScheduledEmailStatusActions["cancel"]).select_for_update()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.request = request
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        self.title = f'Scheduled email "{self.object.subject}"'
        kwargs["scheduled_email"] = self.object
        return super().get_context_data(**kwargs)

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()

    def form_valid(self, form: ScheduledEmailCancelForm) -> HttpResponse:
        if form.cleaned_data.get("confirm"):
            EmailController.cancel_email(
                self.object,
                author=person_from_request(self.request),
            )

        return super().form_valid(form)


class ScheduledEmailAddAttachment(
    OnlyForAdminsMixin,
    FlaggedViewMixin,  # type: ignore[misc]
    SingleObjectMixin[ScheduledEmail],
    AMYFormView[ScheduledEmailAddAttachmentForm],
):
    flag_name = "EMAIL_MODULE"
    permission_required = ["emails.view_scheduledemail", "emails.change_scheduledemail", "emails.add_attachment"]
    template_name = "emails/scheduled_email_add_attachment.html"
    form_class = ScheduledEmailAddAttachmentForm
    queryset = ScheduledEmail.objects.all()
    object: ScheduledEmail
    request: HttpRequest
    title: str

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        self.title = f'Scheduled email "{self.object.subject}"'
        kwargs["scheduled_email"] = self.object
        return super().get_context_data(**kwargs)

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()

    def form_valid(self, form: ScheduledEmailAddAttachmentForm) -> HttpResponse:
        file = self.request.FILES.get("file")
        if file:
            content = file.read()
            filename = file.name or ""
            EmailController.add_attachment(self.object, filename, content)
            messages.info(self.request, f'Attachment "{filename}" added.')
        return super().form_valid(form)
