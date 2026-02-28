from typing import Any

from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from src.extforms.forms import (
    SelfOrganisedSubmissionExternalForm,
    TrainingRequestForm,
    WorkshopInquiryRequestExternalForm,
    WorkshopRequestExternalForm,
)
from src.extrequests.models import SelfOrganisedSubmission, WorkshopInquiryRequest
from src.workshops.base_views import AMYCreateView, AutoresponderMixin, EmailSendMixin
from src.workshops.models import TrainingRequest, WorkshopRequest
from src.workshops.utils.access import LoginNotRequiredMixin
from src.workshops.utils.emails import match_notification_email

# ------------------------------------------------------------
# TrainingRequest views


class TrainingRequestCreate(
    LoginNotRequiredMixin,
    AutoresponderMixin[TrainingRequestForm],
    AMYCreateView[TrainingRequestForm, TrainingRequest],
):
    model = TrainingRequest
    form_class = TrainingRequestForm
    page_title = "Instructor Training Profile Creation Form"
    template_name = "forms/trainingrequest.html"
    success_url = reverse_lazy("training_request_confirm")
    autoresponder_subject = "Thank you for your application"
    autoresponder_body_template_txt = "mailing/training_request.txt"
    autoresponder_body_template_html = "mailing/training_request.html"
    autoresponder_form_field = "email"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = self.page_title
        return context

    def autoresponder_email_context(self, form: TrainingRequestForm) -> dict[str, Any]:
        return dict(object=self.object)

    def get_form_kwargs(self) -> dict[str, Any]:
        # request is required for ENFORCE_MEMBER_CODES flag
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_success_message(self, *args: Any, **kwargs: Any) -> str:
        """Don't display a success message."""
        return ""


class TrainingRequestConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = "forms/trainingrequest_confirm.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = "Thank you for applying for an instructor training"
        return context


# ------------------------------------------------------------
# Workshop landing page view


class WorkshopLanding(LoginNotRequiredMixin, TemplateView):
    template_name = "forms/workshop_landing.html"


# ------------------------------------------------------------
# WorkshopRequest views


class WorkshopRequestCreate(
    LoginNotRequiredMixin,
    EmailSendMixin[WorkshopRequestExternalForm],
    AutoresponderMixin[WorkshopRequestExternalForm],
    AMYCreateView[WorkshopRequestExternalForm, WorkshopRequest],
):
    model = WorkshopRequest
    form_class = WorkshopRequestExternalForm
    page_title = "Request a Carpentries Workshop"
    template_name = "forms/workshoprequest.html"
    success_url = reverse_lazy("workshop_request_confirm")
    email_fail_silently = False

    autoresponder_subject = "Workshop request confirmation"
    autoresponder_body_template_txt = "mailing/workshoprequest.txt"
    autoresponder_body_template_html = "mailing/workshoprequest.html"
    autoresponder_form_field = "email"

    object: WorkshopRequest

    def autoresponder_email_context(self, form: WorkshopRequestExternalForm) -> dict[str, Any]:
        return dict(object=self.object)

    def get_success_message(self, *args: Any, **kwargs: Any) -> str:
        """Don't display a success message."""
        return ""

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = self.page_title
        return context

    def get_form_kwargs(self) -> dict[str, Any]:
        # request is required for ENFORCE_MEMBER_CODES flag
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_email_kwargs(self) -> dict[str, Any]:
        return {
            "to": match_notification_email(self.object),
            "reply_to": [self.object.email],
        }

    def get_subject(self) -> str:
        affiliation = str(self.object.institution) if self.object.institution else self.object.institution_other_name
        subject = f"New workshop request: {affiliation}, {self.object.dates()}"
        return subject

    def get_body(self) -> tuple[str, str]:
        link = self.object.get_absolute_url()
        link_domain = f"https://{get_current_site(self.request)}"

        body_txt = get_template("mailing/workshoprequest_admin.txt").render(
            {
                "object": self.object,
                "link": link,
                "link_domain": link_domain,
            }
        )

        body_html = get_template("mailing/workshoprequest_admin.html").render(
            {
                "object": self.object,
                "link": link,
                "link_domain": link_domain,
            }
        )
        return body_txt, body_html

    def form_valid(self, form: WorkshopRequestExternalForm) -> HttpResponse:
        """Send email to admins if the form is valid."""
        result = super().form_valid(form)
        return result


class WorkshopRequestConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = "forms/workshoprequest_confirm.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = "Thank you for requesting a workshop"
        return context


# ------------------------------------------------------------
# WorkshopInquiryRequest views


class WorkshopInquiryRequestCreate(
    LoginNotRequiredMixin,
    EmailSendMixin[WorkshopInquiryRequestExternalForm],
    AutoresponderMixin[WorkshopInquiryRequestExternalForm],
    AMYCreateView[WorkshopInquiryRequestExternalForm, WorkshopInquiryRequest],
):
    model = WorkshopInquiryRequest
    form_class = WorkshopInquiryRequestExternalForm
    page_title = "Inquiry about Carpentries Workshop"
    template_name = "forms/workshopinquiry.html"
    success_url = reverse_lazy("workshop_inquiry_confirm")
    email_fail_silently = False

    autoresponder_subject = "Workshop inquiry confirmation"
    autoresponder_body_template_txt = "mailing/workshopinquiry.txt"
    autoresponder_body_template_html = "mailing/workshopinquiry.html"
    autoresponder_form_field = "email"

    object: WorkshopInquiryRequest

    def autoresponder_email_context(self, form: WorkshopInquiryRequestExternalForm) -> dict[str, Any]:
        return dict(object=self.object)

    def get_success_message(self, *args: Any, **kwargs: Any) -> str:
        """Don't display a success message."""
        return ""

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = self.page_title
        return context

    def get_email_kwargs(self) -> dict[str, Any]:
        return {
            "to": match_notification_email(self.object),
            "reply_to": [self.object.email],
        }

    def get_subject(self) -> str:
        affiliation = str(self.object.institution) if self.object.institution else self.object.institution_other_name
        subject = f"New workshop inquiry: {affiliation}, {self.object.dates()}"
        return subject

    def get_body(self) -> tuple[str, str]:
        link = self.object.get_absolute_url()
        link_domain = f"https://{get_current_site(self.request)}"

        body_txt = get_template("mailing/workshopinquiry_admin.txt").render(
            {
                "object": self.object,
                "link": link,
                "link_domain": link_domain,
            }
        )

        body_html = get_template("mailing/workshopinquiry_admin.html").render(
            {
                "object": self.object,
                "link": link,
                "link_domain": link_domain,
            }
        )
        return body_txt, body_html

    def form_valid(self, form: WorkshopInquiryRequestExternalForm) -> HttpResponse:
        """Send email to admins if the form is valid."""
        result = super().form_valid(form)
        return result


class WorkshopInquiryRequestConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = "forms/workshopinquiry_confirm.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = "Thank you for inquiring about The Carpentries"
        return context


# ------------------------------------------------------------
# SelfOrganisedSubmission views


class SelfOrganisedSubmissionCreate(
    LoginNotRequiredMixin,
    EmailSendMixin[SelfOrganisedSubmissionExternalForm],
    AutoresponderMixin[SelfOrganisedSubmissionExternalForm],
    AMYCreateView[SelfOrganisedSubmissionExternalForm, SelfOrganisedSubmission],
):
    model = SelfOrganisedSubmission
    form_class = SelfOrganisedSubmissionExternalForm
    page_title = "Submit a self-organised workshop"
    template_name = "forms/selforganised_submission.html"
    success_url = reverse_lazy("selforganised_submission_confirm")
    email_fail_silently = False

    autoresponder_subject = "Self-organised submission confirmation"
    autoresponder_body_template_txt = "mailing/selforganisedsubmission.txt"
    autoresponder_body_template_html = "mailing/selforganisedsubmission.html"
    autoresponder_form_field = "email"

    object: SelfOrganisedSubmission

    def autoresponder_email_context(self, form: SelfOrganisedSubmissionExternalForm) -> dict[str, Any]:
        return dict(object=self.object)

    def get_success_message(self, *args: Any, **kwargs: Any) -> str:
        """Don't display a success message."""
        return ""

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = self.page_title
        return context

    def get_email_kwargs(self) -> dict[str, Any]:
        return {
            "to": match_notification_email(self.object),
            "reply_to": [self.object.email],
        }

    def get_subject(self) -> str:
        affiliation = str(self.object.institution) if self.object.institution else self.object.institution_other_name
        subject = f"New self-organised submission: {affiliation}"
        return subject

    def get_body(self) -> tuple[str, str]:
        link = self.object.get_absolute_url()
        link_domain = f"https://{get_current_site(self.request)}"

        body_txt = get_template("mailing/selforganisedsubmission_admin.txt").render(
            {
                "object": self.object,
                "link": link,
                "link_domain": link_domain,
            }
        )

        body_html = get_template("mailing/selforganisedsubmission_admin.html").render(
            {
                "object": self.object,
                "link": link,
                "link_domain": link_domain,
            }
        )
        return body_txt, body_html

    def form_valid(self, form: SelfOrganisedSubmissionExternalForm) -> HttpResponse:
        """Send email to admins if the form is valid."""
        result = super().form_valid(form)
        return result


class SelfOrganisedSubmissionConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = "forms/selforganisedsubmission_confirm.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = "Thank you for submitting self-organised workshop"
        return context
