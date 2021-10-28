from django.contrib import admin

from .models import CommunityRoleConfig, CommunityRoleInactivation


class CommunityRoleConfigAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "name",
        "link_to_award",
        "award_role_limit",
        "link_to_membership",
        "additional_url",
        "generic_relation_content_type",
        "generic_relation_multiple_items",
        "created_at",
        "last_updated_at",
    )
    date_hierarchy = "created_at"


class CommunityRoleInactivationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_at",
        "last_updated_at",
    )
    date_hierarchy = "created_at"


admin.site.register(CommunityRoleConfig, CommunityRoleConfigAdmin)
admin.site.register(CommunityRoleInactivation, CommunityRoleInactivationAdmin)
