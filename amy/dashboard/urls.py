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
            ]
        ),
    ),
    # redirect "old" trainee dashboard link to new instructor dashboard
    path("trainee/", RedirectView.as_view(pattern_name="instructor-dashboard")),
]
