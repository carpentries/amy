from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.db.models import Model, ProtectedError
from django.http import HttpResponseRedirect
from django.utils.http import is_safe_url
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
    ListView,
)

from workshops.forms import BootstrapHelper
from workshops.util import failed_to_delete, Paginator, get_pagination_items


class AMYCreateView(SuccessMessageMixin, CreateView):
    """
    Class-based view for creating objects that extends default template context
    by adding model class used in objects creation.
    """
    success_message = '{name} was created successfully.'

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


class UpdateViewContext(SuccessMessageMixin, UpdateView):
    """
    Class-based view for updating objects that extends default template context
    by adding proper page title.
    """
    success_message = '{name} was updated successfully.'

    template_name = 'workshops/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super(UpdateViewContext, self).get_context_data(**kwargs)

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


class DeleteViewContext(DeleteView):
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
        if request.POST.get('next', None):
            success_url = request.POST['next']
        else:
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


class FormViewContext(FormView):
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
            self.filter = super().get_queryset()
        else:
            self.filter = self.filter_class(self.get_filter_data(),
                                            super().get_queryset())
        paginated = get_pagination_items(self.request, self.filter)
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

    def prepare_email(self):
        """Set up email contents."""
        subject = self.get_subject()
        body_txt, body_html = self.get_body()
        email = EmailMultiAlternatives(subject, body_txt,
                                       **self.email_kwargs)
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
        if next_url is not None and is_safe_url(next_url):
            return next_url
        else:
            return default_url
