from consents.models import Consent
from consents.models import Term, TermOption
from django.contrib import admin


class TermOptionInline(admin.TabularInline):
    model = TermOption
    extra = 0


class TermAdmin(admin.ModelAdmin):
    list_display = ("slug", "content", "required_type")
    inlines = [
        TermOptionInline,
    ]


class ConsentAdmin(admin.ModelAdmin):
    list_display = ("person", "term", "term_option", "get_term_option_type")
    readonly_fields = ("person", "term", "term_option", "archived_at")
    search_fields = ("person__personal", "person__family", "person__email")
    list_filter = ["term", "term_option__option_type", "archived_at"]

    def get_term_option_type(self, obj):
        return obj.term_option.option_type

    get_term_option_type.short_description = "Term Option Type"
    get_term_option_type.admin_order_field = "term_option__option_type"


admin.site.register(Term, TermAdmin)
admin.site.register(Consent, ConsentAdmin)
