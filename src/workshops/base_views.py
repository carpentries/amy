import typing
from smtplib import SMTPException
from typing import Any, TypeVar, cast

from anymail.exceptions import AnymailRequestsAPIError
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Page
from django.db.models import Model, ProtectedError, QuerySet
from django.forms import BaseForm, BaseModelForm
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    QueryDict,
)
from django.shortcuts import redirect
from django.template.loader import get_template
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    RedirectView,
    UpdateView,
    View,
)
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin
from django_filters.filterset import FilterSet

from src.workshops.forms import AdminLookupForm, BootstrapHelper
from src.workshops.mixins import StateMixin
from src.workshops.models import Person
from src.workshops.utils.pagination import Paginator, get_pagination_items
from src.workshops.utils.urls import safe_next_or_default_url
from src.workshops.utils.views import assign, failed_to_delete

_M = TypeVar("_M", bound=Model)
_ModelFormT = TypeVar("_ModelFormT", bound=BaseModelForm)  # type: ignore
_F = TypeVar("_F", bound=BaseForm)

if typing.TYPE_CHECKING:
    _V = View
else:
    _V = object


class AuthenticatedHttpRequest(HttpRequest):
    user: Person


class FormInvalidMessageMixin[F]:
    """
    Add an error message on invalid form submission.
    """

    form_invalid_message = ""

    def form_invalid(self, form: _F) -> HttpResponse:
        response = super().form_invalid(form)  # type: ignore[misc]
        message = self.get_form_invalid_message(form.cleaned_data)
        if message:
            messages.error(self.request, message)  # type: ignore[attr-defined]
        return response  # type: ignore[no-any-return]

    def get_form_invalid_message(self, cleaned_data: dict[str, str]) -> str:
        return self.form_invalid_message % cleaned_data


class AMYDetailView(DetailView[_M]):
    object: _M


class AMYCreateView(
    SuccessMessageMixin[_ModelFormT], FormInvalidMessageMixin[_ModelFormT], CreateView[_M, _ModelFormT]
):
    """
    Class-based view for creating objects that extends default template context
    by adding model class used in objects creation.
    """

    success_message = "{name} was created successfully."
    form_invalid_message = "Please fix errors in the form below."

    template_name = "generic_form.html"

    def get_form(self, form_class: type[_ModelFormT] | None = None) -> _ModelFormT:
        form = super().get_form(form_class=form_class)
        if not hasattr(form, "helper"):
            # This is a default helper if no other is available.
            form.helper = BootstrapHelper(submit_label="Add")  # type: ignore[attr-defined]
        return form

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # self.model is available in CreateView as the model class being
        # used to create new model instance
        kwargs["model"] = self.model

        if "title" not in kwargs:
            if getattr(self, "title", None):
                kwargs["title"] = self.title  # type: ignore[attr-defined]
            elif self.model and issubclass(self.model, Model):
                kwargs["title"] = f"New {self.model._meta.verbose_name}"
            else:
                kwargs["title"] = "New object"

        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data: dict[str, str]) -> str:
        "Format self.success_message, used by messages framework from Django."
        return self.success_message.format(cleaned_data, name=str(self.object))


class AMYUpdateView(
    SuccessMessageMixin[_ModelFormT], FormInvalidMessageMixin[_ModelFormT], UpdateView[_M, _ModelFormT]
):
    """
    Class-based view for updating objects that extends default template context
    by adding proper page title.
    """

    success_message = "{name} was updated successfully."

    form_invalid_message = "Please fix errors in the form below."

    template_name = "generic_form.html"

    def get_form(self, form_class: type[_ModelFormT] | None = None) -> _ModelFormT:
        form = super().get_form(form_class=form_class)
        if not hasattr(form, "helper"):
            # This is a default helper if no other is available.
            form.helper = BootstrapHelper(submit_label="Update")  # type: ignore[attr-defined]
        return form

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        # self.model is available in UpdateView as the model class being
        # used to update model instance
        kwargs["model"] = self.model

        kwargs["view"] = self

        # self.object is available in UpdateView as the object being currently
        # edited
        if "title" not in kwargs:
            kwargs["title"] = str(self.object)

        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data: dict[str, str]) -> str:
        "Format self.success_message, used by messages framework from Django."
        return self.success_message.format(cleaned_data, name=str(self.object))


class AMYDeleteView(DeleteView[_M, _ModelFormT]):
    """
    Class-based view for deleting objects that extends default template context
    by adding proper page title.

    GET requests are not allowed (returns 405)
    Allows for custom redirection based on `next` param in POST
    ProtectedErrors are handled.
    """

    success_message = "{} was deleted successfully."

    def before_delete(self, *args: Any, **kwargs: Any) -> None:
        return None

    def after_delete(self, *args: Any, **kwargs: Any) -> None:
        return None

    def back_address(self) -> str | None:
        return None

    def form_valid(self, form: _ModelFormT) -> HttpResponse:
        # Workaround for https://code.djangoproject.com/ticket/21926
        # Replicates the `delete` method of DeleteMixin
        self.object = self.get_object()
        object_str = str(self.object)
        success_url = self.get_success_url()
        try:
            self.before_delete()
            self.perform_destroy()
            self.after_delete()
            messages.success(self.request, self.success_message.format(object_str))
            return redirect(success_url)
        except ProtectedError as e:
            back = self.back_address()
            return failed_to_delete(
                self.request,
                self.object,  # type: ignore[arg-type]
                e.protected_objects,
                back=back,
            )

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.http_method_not_allowed(request, *args, **kwargs)

    def perform_destroy(self, *args: Any, **kwargs: Any) -> None:
        self.object.delete()


class AMYFormView(FormView[_F]):
    """
    Class-based view to allow displaying of forms with bootstrap form helper.
    """

    title: str

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        return context


class AMYListView(ListView[_M]):
    paginator_class = Paginator
    filter_class: type[FilterSet] | None = None
    queryset: QuerySet[_M] | None = None
    title: str | None = None

    def get_filter_data(self) -> QueryDict | dict[str, Any]:
        """Datasource for the filter."""
        return self.request.GET

    def get_queryset(self) -> Page[_M]:  # type: ignore
        """Apply a filter to the queryset. Filter is compatible with pagination
        and queryset. Also, apply pagination."""
        if self.filter_class is None:
            self.filter = None
            self.qs = super().get_queryset()
        else:
            self.filter = self.filter_class(self.get_filter_data(), super().get_queryset(), request=self.request)
            self.qs = self.filter.qs
        paginated = get_pagination_items(self.request, self.qs)
        return paginated

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Enhance context by adding a filter to it. Add `title` to context."""
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filter
        if self.title is None:
            raise ImproperlyConfigured("No title attribute.")
        context["title"] = self.title
        return context


class EmailSendMixin[ModelFormT]:
    email_fail_silently: bool = True
    email_kwargs: dict[str, Any] | None = None

    def get_subject(self) -> str:
        """Generate email subject."""
        return ""

    def get_body(self) -> tuple[str, str]:
        """Generate email body (in TXT and HTML versions)."""
        return "", ""

    def get_email_kwargs(self) -> dict[str, Any]:
        """Use this method to define email sender arguments, like:
        * `to`: recipient address(es)
        * `reply_to`: reply-to address
        etc."""
        return self.email_kwargs or {}

    def prepare_email(self) -> EmailMultiAlternatives:
        """Set up email contents."""
        subject = self.get_subject()
        body_txt, body_html = self.get_body()
        kwargs = self.get_email_kwargs()
        email = EmailMultiAlternatives(subject, body_txt, **kwargs)
        email.attach_alternative(body_html, "text/html")
        return email

    def send_email(self, email: EmailMultiAlternatives) -> int:
        """Send a prepared email out."""
        return email.send(fail_silently=self.email_fail_silently)

    def form_valid(self, form: _ModelFormT) -> HttpResponse:
        """Once form is valid, send the email."""
        results = super().form_valid(form)  # type: ignore[misc]
        email = self.prepare_email()
        self.send_email(email)
        return results  # type: ignore[no-any-return]


class RedirectSupportMixin:
    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next", None)  # type: ignore
        default_url = super().get_success_url()  # type: ignore
        return safe_next_or_default_url(next_url, default_url)


class PrepopulationSupportMixin[FormT: BaseForm]:
    request: HttpRequest
    populate_fields: list[str]

    def get_initial(self) -> dict[str, Any]:
        return {field: self.request.GET.get(field) for field in self.populate_fields}

    def get_form(self, form_class: type[FormT] | None = None) -> FormT:
        """Disable fields that are pre-populated."""
        form = cast(
            FormT,
            super().get_form(form_class),  # type: ignore
        )
        for field in self.populate_fields:
            if field in self.request.GET:
                form.fields[field].disabled = True
        return form


class AutoresponderMixin[ModelFormT]:
    """Automatically emails the form sender."""

    @property
    def autoresponder_subject(self) -> str:
        """Autoresponder email subject."""
        raise NotImplementedError

    @property
    def autoresponder_body_template_txt(self) -> str:
        """Autoresponder email body template (TXT)."""
        raise NotImplementedError

    @property
    def autoresponder_body_template_html(self) -> str:
        """Autoresponder email body template (HTML)."""
        raise NotImplementedError

    @property
    def autoresponder_form_field(self) -> str:
        """Form field's name that contains autoresponder recipient email."""
        return "email"

    def autoresponder_email_context(self, form: _ModelFormT) -> dict[str, Any]:
        """Context for"""
        # list of fields allowed to show to the user
        whitelist: list[str] = []
        form_data = [v for k, v in cast(dict[str, Any], form.cleaned_data).items() if k in whitelist]  # type: ignore
        return dict(form_data=form_data)

    def autoresponder_kwargs(self, form: _ModelFormT) -> dict[str, list[str]]:
        """Arguments passed to EmailMultiAlternatives."""
        recipient = form.cleaned_data.get(self.autoresponder_form_field, None) or ""
        return dict(to=[recipient])

    def autoresponder_prepare_email(self, form: _ModelFormT) -> EmailMultiAlternatives:
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

        email = EmailMultiAlternatives(subject, body_txt, **kwargs)  # type: ignore
        email.attach_alternative(body_html, "text/html")
        return email

    def autoresponder(self, form: _ModelFormT, fail_silently: bool = True) -> None:
        """Get email from `self.autoresponder_prepare_email`, then send it."""
        email = self.autoresponder_prepare_email(form)

        try:
            email.send()
        except (SMTPException, AnymailRequestsAPIError) as e:
            if not fail_silently:
                raise e

    def form_valid(self, form: _ModelFormT) -> HttpResponse:
        """Send email to form sender if the form is valid."""
        retval = super().form_valid(form)  # type: ignore[misc]
        self.autoresponder(form, fail_silently=True)
        return retval  # type: ignore[no-any-return]


class StateFilterMixin:
    def get_filter_data(self) -> dict[str, Any]:
        """Enhance filter default data by setting the initial value for the
        `state` field filter."""
        data = super().get_filter_data().copy()  # type: ignore[misc]
        data["state"] = data.get("state", "p")
        return data  # type: ignore[no-any-return]


class ChangeRequestStateView[M2: StateMixin](PermissionRequiredMixin, SingleObjectMixin[M2], RedirectView):
    object: M2

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
    success_message = '%(name)s state was changed to "%(requested_state)s" successfully.'

    def get_states(self) -> dict[str, str]:
        """Return state-state mapping; keys are URL values, and items are
        model-recognizable field values."""
        return self.states

    def get_incorrect_state_message(self) -> str:
        return self.incorrect_state_message

    def incorrect_state(self) -> HttpResponse:
        msg = self.get_incorrect_state_message()
        raise Http404(msg)

    def get_success_message(self) -> str:
        return self.success_message % dict(
            name=str(self.object),
            requested_state=self.object.get_state_display(),
        )

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> str:
        return self.object.get_absolute_url()  # type: ignore[no-any-return,attr-defined]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
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


class AssignView(PermissionRequiredMixin, SingleObjectMixin[_M], FormMixin[AdminLookupForm], RedirectView):
    # URL keyword argument for requested person.
    permanent = False
    person_url_kwarg = "person_id"
    form_class = AdminLookupForm
    object: _M

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> str:
        return self.object.get_absolute_url()  # type: ignore[no-any-return,attr-defined]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            assign(
                self.object,  # type: ignore[arg-type]
                person=form.cleaned_data.get("person"),
            )
        return super().post(request, *args, **kwargs)


class ConditionallyEnabledMixin(_V):
    """Mixin for enabling views based on feature flag."""

    view_enabled: bool | None = None

    def get_view_enabled(self, request: HttpRequest | AuthenticatedHttpRequest) -> bool:
        return self.view_enabled is True

    def dispatch(self, request: HttpRequest | AuthenticatedHttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if self.get_view_enabled(request) is not True:
            raise Http404("Page not found")

        return super().dispatch(request, *args, **kwargs)
