from django.contrib import admin

from consents.admin import ArchiveActionMixin
from trainings.models import Involvement


class InvolvementAdmin(ArchiveActionMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "display_name",
        "url_required",
        "date_required",
        "notes_required",
        "archived_at",
    )
    readonly_fields = ("archived_at",)


admin.site.register(Involvement, InvolvementAdmin)
