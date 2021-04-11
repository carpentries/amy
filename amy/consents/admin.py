from django.contrib import messages
from django.contrib.admin.options import csrf_protect_m
from django.http.response import HttpResponseRedirect
from urllib.parse import unquote

from consents.models import Consent
from consents.models import Term, TermOption
from django.contrib import admin


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
        if request.method == "POST" and "_archive" in request.POST:
            obj = self.get_object(request, unquote(object_id))
            self.archive_single(request, obj)
            return HttpResponseRedirect(request.get_full_path())

        return admin.ModelAdmin.changeform_view(
            self,
            request,
            object_id=object_id,
            form_url=form_url,
            extra_context=extra_context,
        )

    def archive_single(self, request, obj):
        if obj.archived_at is not None:
            self.message_user(
                request,
                f"Error: Cannot archive. {obj} is already archived.",
                level=messages.ERROR,
            )
        else:
            obj.archive()

    def has_delete_permission(self, *args, **kwargs):
        return False


class TermOptionAdmin(ArchiveActionMixin, admin.ModelAdmin):
    list_display = ("term", "option_type", "content", "archived_at")


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
        return False

    get_term_option_type.short_description = "Term Option Type"
    get_term_option_type.admin_order_field = "term_option__option_type"


admin.site.register(Term, TermAdmin)
admin.site.register(TermOption, TermOptionAdmin)
admin.site.register(Consent, ConsentAdmin)
