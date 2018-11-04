from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.db.models import Model, ProtectedError
from django.http import HttpResponseRedirect, Http404
from django.utils.http import is_safe_url
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
    ListView,
    DetailView,
    RedirectView,
)
from django.views.generic.detail import (
    SingleObjectMixin,
)
from django.template.loader import get_template

from workshops.forms import BootstrapHelper
from workshops.util import failed_to_delete, Paginator, get_pagination_items


class FormInvalidMessageMixin:
    """
    Add an error message on invalid form submission.
    """
    form_invalid_message = ''

    def form_invalid(self, form):
        response = super().form_invalid(form)
        message = self.get_form_invalid_message(form.cleaned_data)
        if message:
            messages.error(self.request, message)
        return response

    def get_form_invalid_message(self, cleaned_data):
        return self.form_invalid_message % cleaned_data


class AMYDetailView(DetailView):
    pass


class AMYCreateView(SuccessMessageMixin, FormInvalidMessageMixin, CreateView):
    """
    Class-based view for creating objects that extends default template context
    by adding model class used in objects creation.
    """
    success_message = '{name} was created successfully.'
    form_invalid_message = 'Please fix errors in the form below.'

    template_name = 'workshops/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super(AMYCreateView, self).get_context_data(**kwargs)

        # self.model is available in CreateView as the model class being
        # used to create new model instance
        context['model'] = self.model

        if self.model and issubclass(self.model, Model):
            context['title'] = 'New {}'.format(self.model._meta.verbose_name)
        else:
            context['title'] = 'New object'

        form = context['form']
        if not hasattr(form, 'helper'):
            # This is a default helper if no other is available.
            form.helper = BootstrapHelper(submit_label='Add')

        return context

    def get_success_message(self, cleaned_data):
        "Format self.success_message, used by messages framework from Django."
        return self.success_message.format(cleaned_data, name=str(self.object))


class AMYUpdateView(SuccessMessageMixin, UpdateView):
    """
    Class-based view for updating objects that extends default template context
    by adding proper page title.
    """
    success_message = '{name} was updated successfully.'

    template_name = 'workshops/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super(AMYUpdateView, self).get_context_data(**kwargs)

        # self.model is available in UpdateView as the model class being
        # used to update model instance
        context['model'] = self.model

        context['view'] = self

        # self.object is available in UpdateView as the object being currently
        # edited
        context['title'] = str(self.object)

        form = context['form']
        if not hasattr(form, 'helper'):
            # This is a default helper if no other is available.
            form.helper = BootstrapHelper(submit_label='Update')

        return context

    def get_success_message(self, cleaned_data):
        "Format self.success_message, used by messages framework from Django."
        return self.success_message.format(cleaned_data, name=str(self.object))


class AMYDeleteView(DeleteView):
    """
    Class-based view for deleting objects that extends default template context
    by adding proper page title.

    GET requests are not allowed (returns 405)
    Allows for custom redirection based on `next` param in POST
    ProtectedErrors are handled.
    """
    success_message = '{} was deleted successfully.'

    def delete(self, request, *args, **kwargs):
        # Workaround for https://code.djangoproject.com/ticket/21926
        # Replicates the `delete` method of DeleteMixin
        self.object = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.delete()
            messages.success(
                self.request,
                self.success_message.format(self.object)
            )
            return HttpResponseRedirect(success_url)
        except ProtectedError as e:
            return failed_to_delete(self.request, self.object,
                                    e.protected_objects)

    def get(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)


class AMYFormView(FormView):
    """
    Class-based view to allow displaying of forms with bootstrap form helper.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        return context


class AMYListView(ListView):
    paginator_class = Paginator
    filter_class = None
    queryset = None
    title = None

    def get_filter_data(self):
        """Datasource for the filter."""
        return self.request.GET

    def get_queryset(self):
        """Apply a filter to the queryset. Filter is compatible with pagination
        and queryset. Also, apply pagination."""
        if self.filter_class is None:
            self.filter = None
            self.qs = super().get_queryset()
        else:
            self.filter = self.filter_class(self.get_filter_data(),
                                            super().get_queryset())
            self.qs = self.filter.qs
        paginated = get_pagination_items(self.request, self.qs)
        return paginated

    def get_context_data(self, **kwargs):
        """Enhance context by adding a filter to it. Add `title` to context."""
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter
        if self.title is None:
            raise ImproperlyConfigured('No title attribute.')
        context['title'] = self.title
        return context


class EmailSendMixin:
    email_fail_silently = True
    email_kwargs = None

    def get_subject(self):
        """Generate email subject."""
        return ""

    def get_body(self):
        """Generate email body (in TXT and HTML versions)."""
        return "", ""

    def get_email_kwargs(self):
        """Use this method to define email sender arguments, like:
        * `to`: recipient address(es)
        * `reply_to`: reply-to address
        etc."""
        return self.email_kwargs

    def prepare_email(self):
        """Set up email contents."""
        subject = self.get_subject()
        body_txt, body_html = self.get_body()
        kwargs = self.get_email_kwargs()
        email = EmailMultiAlternatives(subject, body_txt, **kwargs)
        email.attach_alternative(body_html, 'text/html')
        return email

    def send_email(self, email):
        """Send a prepared email out."""
        return email.send(fail_silently=self.email_fail_silently)

    def form_valid(self, form):
        """Once form is valid, send the email."""
        results = super().form_valid(form)
        email = self.prepare_email()
        self.send_email(email)
        return results


class RedirectSupportMixin:
    def get_success_url(self):
        default_url = super().get_success_url()
        next_url = self.request.GET.get('next', None)
        if next_url is not None and is_safe_url(next_url,
                                                allowed_hosts=settings.ALLOWED_HOSTS):
            return next_url
        else:
            return default_url


class PrepopulationSupportMixin:

    def get_initial(self):
        return {
            field: self.request.GET.get(field) for field in self.populate_fields
        }

    def get_form(self, *args, **kwargs):
        """Disable fields that are pre-populated."""
        form = super().get_form(*args, **kwargs)
        for field in self.populate_fields:
            if field in self.request.GET:
                form.fields[field].disabled = True
        return form


class AutoresponderMixin:
    """Automatically emails the sender."""

    @property
    def email_subject(self):
        raise NotImplementedError

    @property
    def email_body_template(self):
        raise NotImplementedError

    def form_valid(self, form):
        """Send email to form sender if the form is valid."""

        retval = super().form_valid(form)

        body_template = get_template(self.email_body_template)
        email_body = body_template.render({})
        recipient = form.cleaned_data['email']

        email = EmailMessage(
            subject=self.email_subject,
            body=email_body,
            to=[recipient],
        )

        try:
            email.send()
        except SMTPException as e:
            pass  # fail silently

        return retval


class StateFilterMixin:
    def get_filter_data(self):
        """Enhance filter default data by setting the initial value for the
        `state` field filter."""
        data = super().get_filter_data().copy()
        data['state'] = data.get('state', 'p')
        return data


class ChangeRequestState(PermissionRequiredMixin, SingleObjectMixin,
                         RedirectView):

    # State URL argument to state model value mapping.
    # Here 'a' and 'accepted' both match to 'a' (recognizable by model's state
    # field), similarly for 'd' (discarded) and 'p' (pending).
    states = {
        'a': 'a',
        'accepted': 'a',
        'd': 'd',
        'discarded': 'd',
        'p': 'p',
        'pending': 'p',
    }

    # Message shown when requested state is not found in `states` dictionary.
    incorrect_state_message = 'Incorrect state value.'

    # URL keyword argument for requested state.
    state_url_kwarg = 'state'

    # Message shown upon successful state change
    success_message = ('%(name)s state was changed to "%(requested_state)s" '
                       'successfully.')

    def get_states(self):
        """Return state-state mapping; keys are URL values, and items are
        model-recognizable field values."""
        return self.states

    def get_incorrect_state_message(self):
        return self.incorrect_state_message

    def incorrect_state(self):
        msg = self.get_incorrect_state_message()
        raise Http404(msg)

    def get_success_message(self):
        return self.success_message % dict(
            name=str(self.object),
            requested_state=self.object.get_state_display(),
        )

    def get(self, request, *args, **kwargs):
        states = self.get_states()
        requested_state = self.kwargs.get(self.state_url_kwarg)

        self.object = self.get_object()
        if requested_state in states:
            self.object.state = states[requested_state]
            self.object.save()

        else:
            self.incorrect_state()

        # show success message
        success_message = self.get_success_message()
        if success_message:
            messages.success(self.request, success_message)

        return super().get(request, *args, **kwargs)
