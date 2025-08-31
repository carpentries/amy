from django.contrib import admin

from fiscal.models import MembershipPersonRole, PartnershipTier


class MembershipPersonRoleAdmin(admin.ModelAdmin[MembershipPersonRole]):
    list_display = ("name", "verbose_name")
    search_fields = ("name", "verbose_name")


class PartnershipTierAdmin(admin.ModelAdmin[PartnershipTier]):
    list_display = ("name",)
    search_fields = ("name",)


admin.site.register(MembershipPersonRole, MembershipPersonRoleAdmin)
admin.site.register(PartnershipTier, PartnershipTierAdmin)
