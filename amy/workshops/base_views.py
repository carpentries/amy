from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.db.models import Model, ProtectedError
from django.http import Http404, HttpResponseRedirect
from django.template.loader import get_template
from django.utils.http import is_safe_url
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    RedirectView,
    UpdateView,
)
from django.views.generic.detail import SingleObjectMixin

from workshops.forms import BootstrapHelper
from workshops.util import Paginator, assign, failed_to_delete, get_pagination_items


class FormInvalidMessageMixin:
    """
    Add an error message on invalid form submission.
    """

    form_invalid_message = ""

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

    success_message = "{name} was created successfully."
    form_invalid_message = "Please fix errors in the form below."

    template_name = "generic_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        if not hasattr(form, "helper"):
            # This is a default helper if no other is available.
            form.helper = BootstrapHelper(submit_label="Add")
        return form

    def get_context_data(self, **kwargs):
        # self.model is available in CreateView as the model class being
        # used to create new model instance
        kwargs["model"] = self.model

        if "title" not in kwargs:
            if self.model and issubclass(self.model, Model):
                kwargs["title"] = "New {}".format(self.model._meta.verbose_name)
            else:
                kwargs["title"] = "New object"

        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        "Format self.success_message, used by messages framework from Django."
        return self.success_message.format(cleaned_data, name=str(self.object))


class AMYUpdateView(SuccessMessageMixin, UpdateView):
    """
    Class-based view for updating objects that extends default template context
    by adding proper page title.
    """

    success_message = "{name} was updated successfully."

    template_name = "generic_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        if not hasattr(form, "helper"):
            # This is a default helper if no other is available.
            form.helper = BootstrapHelper(submit_label="Update")
        return form

    def get_context_data(self, **kwargs):
        # self.model is available in UpdateView as the model class being
        # used to update model instance
        kwargs["model"] = self.model

        kwargs["view"] = self

        # self.object is available in UpdateView as the object being currently
        # edited
        if "title" not in kwargs:
            kwargs["title"] = str(self.object)

        return super().get_context_data(**kwargs)

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

    success_message = "{} was deleted successfully."

    def before_delete(self, *args, **kwargs):
        return None

    def after_delete(self, *args, **kwargs):
        return None

    def delete(self, request, *args, **kwargs):
        # Workaround for https://code.djangoproject.com/ticket/21926
        # Replicates the `delete` method of DeleteMixin
        self.object = self.get_object()
        object_str = str(self.object)
        success_url = self.get_success_url()
        try:
            self.before_delete()
            self.object.delete()
            self.after_delete()
            messages.success(self.request, self.success_message.format(object_str))
            return HttpResponseRedirect(success_url)
        except ProtectedError as e:
            return failed_to_delete(self.request, self.object, e.protected_objects)

    def get(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)


class AMYFormView(FormView):
    """
    Class-based view to allow displaying of forms with bootstrap form helper.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
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
            self.filter = self.filter_class(
                self.get_filter_data(), super().get_queryset()
            )
            self.qs = self.filter.qs
        paginated = get_pagination_items(self.request, self.qs)
        return paginated

    def get_context_data(self, **kwargs):
        """Enhance context by adding a filter to it. Add `title` to context."""
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filter
        if self.title is None:
            raise ImproperlyConfigured("No title attribute.")
        context["title"] = self.title
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
        email.attach_alternative(body_html, "text/html")
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
        next_url = self.request.GET.get("next", None)
        if next_url is not None and is_safe_url(
            next_url, allowed_hosts=settings.ALLOWED_HOSTS
        ):
            return next_url
        else:
            return default_url


class PrepopulationSupportMixin:
    def get_initial(self):
        return {field: self.request.GET.get(field) for field in self.populate_fields}

    def get_form(self, *args, **kwargs):
        """Disable fields that are pre-populated."""
        form = super().get_form(*args, **kwargs)
        for field in self.populate_fields:
            if field in self.request.GET:
                form.fields[field].disabled = True
        return form


class AutoresponderMixin:
    """Automatically emails the form sender."""

    @property
    def autoresponder_subject(self):
        """Autoresponder email subject."""
        raise NotImplementedError

    @property
    def autoresponder_body_template_txt(self):
        """Autoresponder email body template (TXT)."""
        raise NotImplementedError

    @property
    def autoresponder_body_template_html(self):
        """Autoresponder email body template (HTML)."""
        raise NotImplementedError

    @property
    def autoresponder_form_field(self):
        """Form field's name that contains autoresponder recipient email."""
        return "email"

    def autoresponder_email_context(self, form):
        """Context for """
        # list of fields allowed to show to the user
        whitelist = []
        form_data = [v for k, v in form.cleaned_data.items() if k in whitelist]
        return dict(form_data=form_data)

    def autoresponder_kwargs(self, form):
        """Arguments passed to EmailMultiAlternatives."""
        recipient = form.cleaned_data.get(self.autoresponder_form_field, None) or ""
        return dict(to=[recipient])

    def autoresponder_prepare_email(self, form):
        """Prepare EmailMultiAlternatives object with message."""
        # get message subject
        subject = self.autoresponder_subject

        # get message body templates
        body_txt_tpl = get_template(self.autoresponder_body_template_txt)
        body_html_tpl = get_template(self.autoresponder_body_template_html)

        # get message body (both in text and in HTML)
        context = self.autoresponder_email_context(form)
        body_txt = body_txt_tpl.render(context)
        body_html = body_html_tpl.render(context)

        # additional arguments, including recipients
        kwargs = self.autoresponder_kwargs(form)

        email = EmailMultiAlternatives(subject, body_txt, **kwargs)
        email.attach_alternative(body_html, "text/html")
        return email

    def autoresponder(self, form, fail_silently=True):
        """Get email from `self.autoresponder_prepare_email`, then send it."""
        email = self.autoresponder_prepare_email(form)

        try:
            email.send()
        except SMTPException as e:
            if not fail_silently:
                raise e

    def form_valid(self, form):
        """Send email to form sender if the form is valid."""
        retval = super().form_valid(form)
        self.autoresponder(form, fail_silently=True)
        return retval


class StateFilterMixin:
    def get_filter_data(self):
        """Enhance filter default data by setting the initial value for the
        `state` field filter."""
        data = super().get_filter_data().copy()
        data["state"] = data.get("state", "p")
        return data


class ChangeRequestStateView(PermissionRequiredMixin, SingleObjectMixin, RedirectView):

    # State URL argument to state model value mapping.
    # Here 'a' and 'accepted' both match to 'a' (recognizable by model's state
    # field), similarly for 'd' (discarded) and 'p' (pending).
    states = {
        "a": "a",
        "accepted": "a",
        "d": "d",
        "discarded": "d",
        "p": "p",
        "pending": "p",
    }

    # Message shown when requested state is not found in `states` dictionary.
    incorrect_state_message = "Incorrect state value."

    # URL keyword argument for requested state.
    state_url_kwarg = "state"

    # Message shown upon successful state change
    success_message = (
        '%(name)s state was changed to "%(requested_state)s" ' "successfully."
    )

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

    def get_redirect_url(self, *args, **kwargs):
        return self.object.get_absolute_url()

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


class AssignView(PermissionRequiredMixin, SingleObjectMixin, RedirectView):
    # URL keyword argument for requested person.
    permanent = False
    person_url_kwarg = "person_id"

    def get_redirect_url(self, *args, **kwargs):
        return self.object.get_absolute_url()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        requested_person_id = self.kwargs.get(self.person_url_kwarg)
        assign(request, self.object, requested_person_id)
        return super().get(request, *args, **kwargs)
