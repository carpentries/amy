from django.urls import include, path
from django.views.generic import RedirectView

from dashboard import views

urlpatterns = [
    path("", views.dispatch, name="dispatch"),
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
    # instructor dashboard and instructor-available views
    path(
        "instructor/",
        include(
            [
                path("", views.instructor_dashboard, name="instructor-dashboard"),
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
    # redirect "old" trainee dashboard link to new instructor dashboard
    path("trainee/", RedirectView.as_view(pattern_name="instructor-dashboard")),
]
