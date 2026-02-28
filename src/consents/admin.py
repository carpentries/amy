import logging
from typing import Any
from urllib.parse import unquote

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.http.response import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect

from src.consents.models import Consent, Term, TermOption

logger = logging.getLogger("amy")


class ArchiveActionMixin[T: Model](admin.ModelAdmin[T]):
    """
    Used for AdminModels that have the CreatedUpdatedArchivedMixin
    and need to archive rather than delete the model.
    """

    change_form_template = "consents/admin_change_form_term.html"
    actions = ["archive"]
    readonly_fields = ("archived_at",)

    @csrf_protect
    def changeform_view(
        self,
        request: HttpRequest,
        object_id: str | None = None,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        if request.method == "POST" and "_archive" in request.POST:
            obj = self.get_object(request, unquote(object_id or ""))
            if obj:
                self.archive_single(request, obj)
            return HttpResponseRedirect(request.get_full_path())

        if object_id is not None:
            obj = self.get_object(request, unquote(object_id))
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

    def archive_single(self, request: HttpRequest, obj: T) -> None:
        # `.archived_at` comes from CreatedUpdatedArchivedMixin
        if obj.archived_at is not None:  # type: ignore[attr-defined]
            messages.error(
                request,
                f"Error: Cannot archive. {obj.__class__.__name__}  {obj} is already archived.",
            )
        else:
            try:
                # `.archive()` comes from CreatedUpdatedArchivedMixin
                obj.archive()  # type: ignore[attr-defined]
            except ValidationError as error:
                messages.error(request, f"Error: Could not archive {obj}.\n{str(error)}")
            else:
                messages.success(request, f"Success: Archived {obj}.")

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        """Determines if the admin class can delete objects.
        See https://docs.djangoproject.com/en/2.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.has_delete_permission
        """  # noqa
        return False

    def warning_message(self, obj: Any) -> str:
        """
        Message displayed as a pop-up to the user before they archive the given object.
        """
        return f"Warning: This will archive {obj.__class__.__name__} {obj}"


class TermOptionAdmin(ArchiveActionMixin[TermOption]):
    list_display = ("term", "option_type", "content", "archived_at")

    def warning_message(self, obj: Any) -> str:
        message = super().warning_message(obj)
        if obj.term.required_type != Term.OPTIONAL_REQUIRE_TYPE:
            return f"{message}. An email will be sent to all users who previously consented with this term option."
        return message


class TermOptionInline(admin.TabularInline[TermOption, Term]):
    model = TermOption
    extra = 0
    readonly_fields = (
        "archived_at",
        "is_archived",
    )
    show_change_link = True

    def is_archived(self, object: TermOption) -> bool:
        return object.archived_at is not None

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        """Determines if the admin class can delete objects.
        See https://docs.djangoproject.com/en/2.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.has_delete_permission
        """  # noqa
        return False


class TermAdmin(ArchiveActionMixin[Term]):
    list_display = (
        "slug",
        "content",
        "training_request_content",
        "short_description",
        "required_type",
        "archived_at",
    )
    inlines = [
        TermOptionInline,
    ]
    actions = ["email_users_missing_consent", "email_users_to_reconsent"]
    readonly_fields = ("archived_at",)

    def email_users_missing_consent(self, request: HttpRequest, queryset: QuerySet[Term]) -> None:
        messages.error(
            request,
            "Error: action disabled because old email system is disabled.",
        )
        return
        # if not self.check_terms_for_consent_email(request, queryset):
        #     return
        # for term in queryset:
        #     send_consent_email(request, term)

    def email_users_to_reconsent(self, request: HttpRequest, queryset: QuerySet[Term]) -> None:
        messages.error(
            request,
            "Error: action disabled because old email system is disabled.",
        )
        return
        # if not self.check_terms_for_consent_email(request, queryset):
        #     return
        # Consent.archive_all_for_term(queryset)
        # for term in queryset:
        #     send_consent_email(request, term)

    # def check_terms_for_consent_email(self, request, terms: Iterable[Term]) -> bool:
    #     for term in terms:
    #         if not NewConsentRequiredAction.check(term):
    #             messages.error(
    #                 request,
    #                 f"Error: Selected term {term.slug} is not valid for emailing "
    #                 "users",
    #             )
    #             return False
    #     return True

    def warning_message(self, obj: Any) -> str:
        message = super().warning_message(obj)
        return f"{message} and all associated term options and user consents."

    def get_form(self, request: HttpRequest, obj: Term | None = None, change: bool = False, **kwargs: Any) -> Any:
        form = super().get_form(request, obj=None, change=False, **kwargs)
        if not change:
            form.base_fields["required_type"].choices = [("optional", "Optional")]  # type: ignore[attr-defined]
            form.base_fields["required_type"].help_text = (
                "If you'd like to set the term to required, you must first create it"
                " as optional, and then set as required."
            )
        elif request.method == "GET":
            warning_message = (
                "Warning: Changing this term to required will force all users"
                " (including admins)"
                " to consent to this term IMMEDIATELY before using the site."
            )
            if obj and obj.required_type == Term.OPTIONAL_REQUIRE_TYPE:
                messages.warning(request, warning_message)
            form.base_fields["required_type"].help_text = warning_message
        return form


class ConsentAdmin(admin.ModelAdmin[Consent]):
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

    def get_term_option_type(self, obj: Consent) -> str | None:
        return obj.term_option.option_type if obj.term_option else None

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        # Note this class does not inherit from ArchiveActionMixin purposefully.
        # Individual user consents should not be archived or deleted
        # from the admin view.
        return False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Consent | None = None) -> bool:
        return False

    get_term_option_type.short_description = "Term Option Type"  # type: ignore[attr-defined]
    get_term_option_type.admin_order_field = "term_option__option_type"  # type: ignore[attr-defined]


admin.site.register(Term, TermAdmin)
admin.site.register(TermOption, TermOptionAdmin)
admin.site.register(Consent, ConsentAdmin)
