# flake8: noqa
from django.urls import include, path

from fiscal import views

urlpatterns = [
    # organizations
    path("organizations/", include([
        path("", views.AllOrganizations.as_view(), name="all_organizations"),
        path("add/", views.OrganizationCreate.as_view(), name="organization_add"),
    ])),
    path("organization/<str:org_domain>/", include([
        path("", views.OrganizationDetails.as_view(), name="organization_details"),
        path("edit/", views.OrganizationUpdate.as_view(), name="organization_edit"),
        path("delete/", views.OrganizationDelete.as_view(), name="organization_delete"),
    ])),
    # memberships
    path("memberships/", include([
        path("", views.AllMemberships.as_view(), name="all_memberships"),
        path("add/", views.MembershipCreate.as_view(), name="membership_add"),
    ])),
    path("membership/<int:membership_id>/", include([
        path("", views.MembershipDetails.as_view(), name="membership_details"),
        path("edit/", views.MembershipUpdate.as_view(), name="membership_edit"),
        path("members/", views.MembershipMembers.as_view(), name="membership_members"),
        path("tasks/", views.MembershipTasks.as_view(), name="membership_tasks"),
        path("extend/", views.MembershipExtend.as_view(), name="membership_extend"),
        path("delete/", views.MembershipDelete.as_view(), name="membership_delete"),
        path("roll-over/", views.MembershipCreateRollOver.as_view(), name="membership_create_roll_over"),
    ])),
]
