from django.urls import include, path
from django.views.generic import RedirectView

from src.dashboard import views

urlpatterns = [
    # admin dashboard main page
    path(
        "admin/",
        include(
            [
                path("", views.admin_dashboard, name="admin-dashboard"),
                path("search/", views.search, name="search"),
                path(
                    "feature_flags/",
                    views.AllFeatureFlags.as_view(),
                    name="feature_flags",
                ),
            ]
        ),
    ),
    # redirect from old instructor dashboard link to new user dashboard URL
    path("instructor/", RedirectView.as_view(pattern_name="user-dashboard")),
    # redirect from old trainee dashboard link to new user dashboard URL
    path("trainee/", RedirectView.as_view(pattern_name="user-dashboard")),
    # user (instructor) dashboard and user-available views
    path("", views.user_dashboard, name="user-dashboard"),
    path(
        "",
        include(
            [
                path(
                    "training_progress/",
                    views.training_progress,
                    name="training-progress",
                ),
                path(
                    "autoupdate_profile/",
                    views.autoupdate_profile,
                    name="autoupdate_profile",
                ),
                path(
                    "teaching_opportunities/",
                    views.UpcomingTeachingOpportunitiesList.as_view(),
                    name="upcoming-teaching-opportunities",
                ),
                path(
                    "teaching_opportunities/<int:recruitment_pk>/signup",
                    views.SignupForRecruitment.as_view(),
                    name="signup-for-recruitment",
                ),
                path(
                    "teaching_opportunities/signups/<int:signup_pk>/resign",
                    views.ResignFromRecruitment.as_view(),
                    name="resign-from-recruitment",
                ),
                path(
                    "get_involved/",
                    include(
                        [
                            path(
                                "create/",
                                views.GetInvolvedCreateView.as_view(),
                                name="getinvolved_add",
                            ),
                            path(
                                "<int:pk>/edit/",
                                views.GetInvolvedUpdateView.as_view(),
                                name="getinvolved_update",
                            ),
                            path(
                                "<int:pk>/delete/",
                                views.GetInvolvedDeleteView.as_view(),
                                name="getinvolved_delete",
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
]
