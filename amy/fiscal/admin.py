from django.contrib import admin

from fiscal.models import MembershipPersonRole


class MembershipPersonRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "verbose_name")
    search_fields = ("name", "verbose_name")


admin.site.register(MembershipPersonRole, MembershipPersonRoleAdmin)
