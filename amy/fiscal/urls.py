# flake8: noqa
from django.urls import include, path

from fiscal import views

urlpatterns = [
    # organizations
    path(
        "organizations/",
        include(
            [
                path("", views.AllOrganizations.as_view(), name="all_organizations"),
                path("add/", views.OrganizationCreate.as_view(), name="organization_add"),
            ]
        ),
    ),
    path(
        "organization/<str:org_domain>/",
        include(
            [
                path("", views.OrganizationDetails.as_view(), name="organization_details"),
                path("edit/", views.OrganizationUpdate.as_view(), name="organization_edit"),
                path("delete/", views.OrganizationDelete.as_view(), name="organization_delete"),
            ]
        ),
    ),
    # memberships
    path(
        "memberships/",
        include(
            [
                path("", views.AllMemberships.as_view(), name="all_memberships"),
                path("add/", views.MembershipCreate.as_view(), name="membership_add"),
            ]
        ),
    ),
    path(
        "membership/<int:membership_id>/",
        include(
            [
                path("", views.MembershipDetails.as_view(), name="membership_details"),
                path("edit/", views.MembershipUpdate.as_view(), name="membership_edit"),
                path("members/", views.MembershipMembers.as_view(), name="membership_members"),
                path("tasks/", views.MembershipTasks.as_view(), name="membership_tasks"),
                path("extend/", views.MembershipExtend.as_view(), name="membership_extend"),
                path("delete/", views.MembershipDelete.as_view(), name="membership_delete"),
                path("roll-over/", views.MembershipCreateRollOver.as_view(), name="membership_create_roll_over"),
            ]
        ),
    ),
    # consortiums
    path(
        "consortiums/",
        include(
            [
                path("", views.ConsortiumList.as_view(), name="consortium-list"),
                path("create/", views.ConsortiumCreate.as_view(), name="consortium-create"),
            ]
        ),
    ),
    path(
        "consortiums/<int:pk>/",
        include(
            [
                path("", views.ConsortiumDetails.as_view(), name="consortium-details"),
                path("edit/", views.ConsortiumUpdate.as_view(), name="consortium-update"),
                path("delete/", views.ConsortiumDelete.as_view(), name="consortium-delete"),
            ]
        ),
    ),
    # partnerships
    path(
        "partnerships/",
        include(
            [
                path("", views.PartnershipList.as_view(), name="partnership-list"),
                path("create/", views.PartnershipCreate.as_view(), name="partnership-create"),
            ]
        ),
    ),
    path(
        "partnerships/<int:pk>/",
        include(
            [
                path("", views.PartnershipDetails.as_view(), name="partnership-details"),
                path("edit/", views.PartnershipUpdate.as_view(), name="partnership-update"),
                path("delete/", views.PartnershipDelete.as_view(), name="partnership-delete"),
                path("extend/", views.PartnershipExtend.as_view(), name="partnership-extend"),
                path("extend-credits/", views.PartnershipExtendCredits.as_view(), name="partnership-extend-credits"),
                path("roll-over/", views.PartnershipRollOver.as_view(), name="partnership-roll-over"),
            ]
        ),
    ),
]
