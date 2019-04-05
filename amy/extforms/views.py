from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import TemplateView, RedirectView

from extforms.forms import (
    TrainingRequestForm,
    WorkshopRequestExternalForm,
)
from workshops.models import (
    TrainingRequest,
    WorkshopRequest,
)
from workshops.util import (
    LoginNotRequiredMixin,
    match_notification_email,
)
from workshops.base_views import (
    AMYCreateView,
    EmailSendMixin,
    AutoresponderMixin,
)


# ------------------------------------------------------------
# TrainingRequest views

class TrainingRequestCreate(
    LoginNotRequiredMixin,
    AutoresponderMixin,
    AMYCreateView,
):
    model = TrainingRequest
    form_class = TrainingRequestForm
    template_name = 'forms/trainingrequest.html'
    success_url = reverse_lazy('training_request_confirm')
    autoresponder_subject = 'Thank you for your application'
    autoresponder_body_template_txt = 'mailing/training_request.txt'
    autoresponder_body_template_html = 'mailing/training_request.html'
    autoresponder_form_field = 'email'

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # replace empty string with None
        group_name = self.request.GET.get('group', None) or None
        kwargs['initial_group_name'] = group_name
        return kwargs


class TrainingRequestConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = 'forms/trainingrequest_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thank you for applying for an instructor training'
        return context


# ------------------------------------------------------------
# WorkshopRequest views

class WorkshopRequestCreate(
    LoginNotRequiredMixin,
    EmailSendMixin,
    AMYCreateView,
):
    model = WorkshopRequest
    form_class = WorkshopRequestExternalForm
    page_title = 'Request a Carpentries Workshop'
    template_name = 'forms/workshoprequest.html'
    success_url = reverse_lazy('workshop_request_confirm')
    email_fail_silently = False

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.page_title
        return context

    def get_email_kwargs(self):
        return {
            'to': match_notification_email(self.object),
            'reply_to': [self.object.email],
        }

    def get_subject(self):
        affiliation = (
            str(self.object.institution)
            if self.object.institution
            else self.object.institution_name
        )
        subject = (
            'New workshop request: {affiliation}, {dates}'
        ).format(
            affiliation=affiliation,
            dates=self.object.preferred_dates,
        )
        return subject

    def get_body(self):
        link = self.object.get_absolute_url()
        link_domain = 'https://{}'.format(get_current_site(self.request))

        body_txt = get_template(
            'mailing/workshoprequest_admin.txt'
        ).render({
            'object': self.object,
            'link': link,
            'link_domain': link_domain,
        })

        body_html = get_template(
            'mailing/workshoprequest_admin.html'
        ).render({
            'object': self.object,
            'link': link,
            'link_domain': link_domain,
        })
        return body_txt, body_html

    def form_valid(self, form):
        """Send email to admins if the form is valid."""
        result = super().form_valid(form)
        return result


class WorkshopRequestConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = 'forms/workshoprequest_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thank you for requesting a workshop'
        return context


# ------------------------------------------------------------
# Deprecated views

class RedirectToWorkshopRequest(LoginNotRequiredMixin, RedirectView):
    """A single class for handling redirect to new, unified workshop request
    form, which replaces all other event-request(-kinda) forms."""
    permanent = False
    query_string = False
    url = reverse_lazy('workshop_request')


# This form is disabled
class SWCEventRequest(RedirectToWorkshopRequest):
    pass


# This form is disabled
class DCEventRequest(RedirectToWorkshopRequest):
    pass


# This form is disabled
class EventSubmission(RedirectToWorkshopRequest):
    pass


# This form is disabled
class DCSelfOrganizedEventRequest(RedirectToWorkshopRequest):
    pass


# This form is disabled
class ProfileUpdateRequestView(LoginNotRequiredMixin, RedirectView):
    permanent = False
    query_string = False
    url = 'https://static.carpentries.org/instructors/'
