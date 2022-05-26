from django.contrib import admin
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from .models import CommunityRoleConfig, CommunityRoleInactivation


class CommunityRoleConfigAdmin(DynamicArrayMixin, admin.ModelAdmin):
    list_display = (
        "display_name",
        "name",
        "link_to_award",
        "award_badge_limit",
        "link_to_membership",
        "additional_url",
        "generic_relation_content_type",
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
