from django.urls import include, path

from . import views

urlpatterns = [
    path("roles/add/", views.CommunityRoleCreate.as_view(), name="communityrole_add"),
    path(
        "role/<int:pk>/",
        include(
            [
                path(
                    "",
                    views.CommunityRoleDetails.as_view(),
                    name="communityrole_details",
                ),
                path(
                    "edit/",
                    views.CommunityRoleUpdate.as_view(),
                    name="communityrole_edit",
                ),
                path(
                    "delete/",
                    views.CommunityRoleDelete.as_view(),
                    name="communityrole_delete",
                ),
            ]
        ),
    ),
]
