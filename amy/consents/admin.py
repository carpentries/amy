import django_rq
import logging

from django.contrib import admin, messages
from django.contrib.admin.options import csrf_protect_m
from django.http.response import HttpResponseRedirect
from typing import Any, Iterable
from urllib.parse import unquote

from autoemails.actions import NewConsentRequiredAction
from autoemails.base_views import ActionManageMixin
from autoemails.models import Trigger
from consents.models import Consent, Term, TermOption


logger = logging.getLogger("amy.signals")  # TODO... why signals logger?
scheduler = django_rq.get_scheduler("default")
redis_connection = django_rq.get_connection("default")

class ArchiveActionMixin:
    """
    Used for AdminModels that have the CreatedUpdatedArchivedMixin
    and need to archive rather than delete the model.
    """

    change_form_template = "consents/admin_change_form_term.html"
    actions = ["archive"]
    readonly_fields = ("archived_at",)

    @csrf_protect_m
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if request.method == "POST" and "_archive" in request.POST:
            self.archive_single(request, obj)
            return HttpResponseRedirect(request.get_full_path())

        if extra_context is None:
            extra_context = {"warning_message": self.warning_message(obj)}
        else:
            extra_context["warning_message"] = self.warning_message(obj)

        return admin.ModelAdmin.changeform_view(
            self,
            request,
            object_id=object_id,
            form_url=form_url,
            extra_context=extra_context,
        )

    def archive_single(self, request, obj):
        if obj.archived_at is not None:
            messages.error(
                request,
                f"Error: Cannot archive. {obj.__class__.__name__}"
                f"  {obj} is already archived.",
            )
        else:
            obj.archive()

    def has_delete_permission(self, *args, **kwargs):
        """Determines if the admin class can delete objects.
        See https://docs.djangoproject.com/en/2.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.has_delete_permission"""  # noqa
        return False

    def warning_message(self, obj: Any) -> str:
        """
        Message displayed as a pop-up to the user before they archive the given object.
        """
        return f"Warning: This will archive {obj.__class__.__name__} {obj}"


class TermOptionAdmin(ArchiveActionMixin, admin.ModelAdmin):
    list_display = ("term", "option_type", "content", "archived_at")

    def warning_message(self, obj: Any) -> str:
        message = super().warning_message(obj)
        if obj.term.required_type != Term.OPTIONAL_REQUIRE_TYPE:
            return (
                f"{message}. An email will be sent to all users who previously"
                " consented with this term option."
            )
        return message


def send_consent_email(request, term: Term) -> None:
    jobs, rqjobs = ActionManageMixin.add(
        action_class=NewConsentRequiredAction,
        logger=logger,
        scheduler=scheduler,
        triggers=Trigger.objects.filter(
            active=True,
            action="consent-required",
        ),
        context_objects={
            "term": term,
        },
        object_=term,
        request=request,
    )


class TermOptionInline(admin.TabularInline):
    model = TermOption
    extra = 0
    readonly_fields = (
        "archived_at",
        "is_archived",
    )
    show_change_link = True

    def is_archived(self, object):
        return object.archived_at is not None


class TermAdmin(ArchiveActionMixin, admin.ModelAdmin):
    list_display = ("slug", "content", "required_type", "archived_at")
    inlines = [
        TermOptionInline,
    ]
    actions = ["email_users_missing_consent", "email_users_to_reconsent"]

    def email_users_missing_consent(self, request, queryset):
        if not self.check_terms_for_consent_email(request, queryset):
            return
        for term in queryset:
            send_consent_email(request, term)

    def email_users_to_reconsent(self, request, queryset):
        if not self.check_terms_for_consent_email(request, queryset):
            return
        Consent.archive_all_for_term(queryset)
        for term in queryset:
            send_consent_email(request, term)

    def check_terms_for_consent_email(self, request, terms: Iterable[Term]) -> bool:
        for term in terms:
            if not NewConsentRequiredAction.check(term):
                messages.error(
                    request,
                    f"Error: Selected term {term.slug} is not valid for emailing users",
                )
                return False
        return True

    def warning_message(self, obj: Any) -> str:
        message = super().warning_message(obj)
        return f"{message} and all associated term options and user consents."


class ConsentAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "person",
        "term",
        "term_option",
        "get_term_option_type",
        "archived_at",
    )
    readonly_fields = ("person", "term", "term_option", "archived_at")
    search_fields = ("person__personal", "person__family", "person__email")
    list_filter = ["term", "term_option__option_type", "archived_at"]

    def get_term_option_type(self, obj):
        return obj.term_option.option_type if obj.term_option else None

    def has_delete_permission(self, *args, **kwargs):
        # Note this class does not inherit from ArchiveActionMixin purposefully.
        # Individual user consents should not be archived or deleted
        # from the admin view.
        return False

    get_term_option_type.short_description = "Term Option Type"
    get_term_option_type.admin_order_field = "term_option__option_type"


admin.site.register(Term, TermAdmin)
admin.site.register(TermOption, TermOptionAdmin)
admin.site.register(Consent, ConsentAdmin)
