from django.contrib import admin

from src.consents.admin import ArchiveActionMixin
from src.trainings.models import Involvement


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
