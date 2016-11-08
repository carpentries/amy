from django.conf import settings
from django.core.urlresolvers import reverse, reverse_lazy
from django.shortcuts import render
from django.template.loader import get_template
from django.views.generic import TemplateView

from workshops.forms import (
    SWCEventRequestForm,
    DCEventRequestForm,
    EventSubmitForm,
    DCSelfOrganizedEventRequestForm,
    TrainingRequestForm,
    ProfileUpdateRequestForm,
)
from workshops.models import (
    EventRequest,
    EventSubmission as EventSubmissionModel,
    DCSelfOrganizedEventRequest as DCSelfOrganizedEventRequestModel,
)
from workshops.util import (
    login_not_required,
    LoginNotRequiredMixin,
)
from workshops.base_views import (
    AMYCreateView,
    EmailSendMixin,
)


class SWCEventRequest(LoginNotRequiredMixin, EmailSendMixin, AMYCreateView):
    model = EventRequest
    form_class = SWCEventRequestForm
    page_title = 'Request a Software Carpentry Workshop'
    template_name = 'forms/workshop_swc_request.html'
    success_url = reverse_lazy('swc_workshop_request_confirm')
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
        subject = (
            '[{tag}] New workshop request: {affiliation}, {country}'
        ).format(
            tag=self.object.workshop_type.upper(),
            country=self.object.country.name,
            affiliation=self.object.affiliation,
        )
        return subject

    def get_body(self):
        link = self.object.get_absolute_url()
        link_domain = settings.SITE_URL

        body_txt = get_template(
            'mailing/eventrequest.txt'
        ).render({
            'object': self.object,
            'link': link,
            'link_domain': link_domain,
        })

        body_html = get_template(
            'mailing/eventrequest.html'
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


class SWCEventRequestConfirm(LoginNotRequiredMixin, TemplateView):
    """Display confirmation of received workshop request."""
    template_name = 'forms/workshop_swc_request_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thank you for requesting a workshop'
        return context


class DCEventRequest(SWCEventRequest):
    form_class = DCEventRequestForm
    page_title = 'Request a Data Carpentry Workshop'
    template_name = 'forms/workshop_dc_request.html'
    success_url = reverse_lazy('dc_workshop_request_confirm')


class DCEventRequestConfirm(SWCEventRequestConfirm):
    """Display confirmation of received workshop request."""
    template_name = 'forms/workshop_dc_request_confirm.html'


@login_not_required
def profileupdaterequest_create(request):
    """
    Profile update request form. Accessible to all users (no login required).

    This one is used when instructors want to change their information.
    """
    form = ProfileUpdateRequestForm()
    page_title = 'Update Instructor Profile'

    if request.method == 'POST':
        form = ProfileUpdateRequestForm(request.POST)

        if form.is_valid():
            form.save()

            # TODO: email notification?

            context = {
                'title': 'Thank you for updating your instructor profile',
            }
            return render(request,
                          'forms/profileupdate_confirm.html',
                          context)
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title': page_title,
        'form': form,
    }
    return render(request, 'forms/profileupdate.html', context)


# This form is disabled as per @maneesha's request
# class EventSubmission(LoginNotRequiredMixin, EmailSendMixin,
#                       AMYCreateView):
class EventSubmission(LoginNotRequiredMixin, TemplateView):
    """Display form for submitting existing workshops."""
    model = EventSubmissionModel
    form_class = EventSubmitForm
    template_name = 'forms/event_submit.html'
    success_url = reverse_lazy('event_submission_confirm')
    email_fail_silently = False
    email_kwargs = {
        'to': settings.REQUEST_NOTIFICATIONS_RECIPIENTS,
    }

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Tell us about your workshop'
        return context

    def get_subject(self):
        return ('New workshop submission from {}'
                .format(self.object.contact_name))

    def get_body(self):
        link = self.object.get_absolute_url()
        link_domain = settings.SITE_URL
        body_txt = get_template('mailing/event_submission.txt') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        body_html = get_template('mailing/event_submission.html') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        return body_txt, body_html


class EventSubmissionConfirm(LoginNotRequiredMixin, TemplateView):
    """Display confirmation of received workshop submission."""
    template_name = 'forms/event_submission_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thanks for your submission'
        return context


class DCSelfOrganizedEventRequest(LoginNotRequiredMixin, EmailSendMixin,
                                  AMYCreateView):
    "Display form for requesting self-organized workshops for Data Carpentry."
    model = DCSelfOrganizedEventRequestModel
    form_class = DCSelfOrganizedEventRequestForm
    # we're reusing DC templates for normal workshop requests
    template_name = 'forms/workshop_dc_request.html'
    success_url = reverse_lazy('dc_workshop_selforganized_request_confirm')
    email_fail_silently = False
    email_kwargs = {
        'to': settings.REQUEST_NOTIFICATIONS_RECIPIENTS,
    }

    def get_success_message(self, *args, **kwargs):
        """Don't display a success message."""
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Register a self-organized Data Carpentry workshop'
        return context

    def get_subject(self):
        return ('DC: new self-organized workshop request from {} @ {}'
                .format(self.object.name, self.object.organization))

    def get_body(self):
        link = self.object.get_absolute_url()
        link_domain = settings.SITE_URL
        body_txt = get_template('mailing/dc_self_organized.txt') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        body_html = get_template('mailing/dc_self_organized.html') \
            .render({
                'object': self.object,
                'link': link,
                'link_domain': link_domain,
            })
        return body_txt, body_html


class DCSelfOrganizedEventRequestConfirm(LoginNotRequiredMixin, TemplateView):
    """Display confirmation of a received self-organized workshop request."""
    # we're reusing DC templates for normal workshop requests
    template_name = 'forms/workshop_dc_request_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thanks for your submission'
        return context


@login_not_required
def trainingrequest_create(request):
    """A form to let all users (no login required) to request Instructor
    Training."""

    form = TrainingRequestForm()
    page_title = 'Apply for Instructor Training'

    if request.method == 'POST':
        form = TrainingRequestForm(request.POST)

        if form.is_valid():
            form.save()

            # TODO: email notification?

            context = {
                'title': 'Thank you for applying for an instructor training.',
            }
            return render(request,
                          'forms/trainingrequest_confirm.html',
                          context)
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title': page_title,
        'form': form,
    }
    return render(request, 'forms/trainingrequest.html', context)
