from django.urls import path

from emails import views

urlpatterns = [
    path(
        "templates/",
        views.EmailTemplateListView.as_view(),
        name="email-templates-list",
    ),
    path(
        "scheduled-emails/",
        views.ScheduledEmailListView.as_view(),
        name="scheduled-emails-list",
    ),
]
