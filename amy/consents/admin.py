from consents.models import Term, TermOption
from django.contrib import admin


class TermOptionInline(admin.TabularInline):
    model = TermOption


class TermAdmin(admin.ModelAdmin):
    list_display = ("slug", "content", "required_type")
    inlines = [
        TermOptionInline,
    ]


admin.site.register(Term, TermAdmin)
