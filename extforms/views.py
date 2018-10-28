from django.conf import settings
from django.contrib import messages
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import TemplateView, RedirectView

from workshops.forms import (
    TrainingRequestForm,
    WorkshopRequestExternalForm,
)
from workshops.models import (
    TrainingRequest,
    WorkshopRequest,
)
from workshops.util import (
    LoginNotRequiredMixin,
)
from workshops.base_views import (
    AMYCreateView,
    EmailSendMixin,
    AutoresponderMixin,
)


#------------------------------------------------------------
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
    email_subject = 'Thank you for your application'
    email_body_template = 'mailing/training_request.txt'

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        group_name = self.request.GET.get('group', None) or None  # replace empty string with None
        kwargs['initial_group_name'] = group_name
        return kwargs


class TrainingRequestConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = 'forms/trainingrequest_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thank you for applying for an instructor training'
        return context


#------------------------------------------------------------
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
    email_kwargs = {
        'to': settings.REQUEST_NOTIFICATIONS_RECIPIENTS,
        'reply_to': None,
    }

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.page_title
        return context

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
        link_domain = settings.SITE_URL

        body_txt = get_template(
            'mailing/workshoprequest.txt'
        ).render({
            'object': self.object,
            'link': link,
            'link_domain': link_domain,
        })

        body_html = get_template(
            'mailing/workshoprequest.html'
        ).render({
            'object': self.object,
            'link': link,
            'link_domain': link_domain,
        })
        return body_txt, body_html

    def form_valid(self, form):
        """Send email to admins if the form is valid."""
        data = form.cleaned_data
        self.email_kwargs['reply_to'] = (data['email'], )
        result = super().form_valid(form)
        return result


class WorkshopRequestConfirm(LoginNotRequiredMixin, TemplateView):
    template_name = 'forms/workshoprequest_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thank you for requesting a workshop'
        return context


#------------------------------------------------------------
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
