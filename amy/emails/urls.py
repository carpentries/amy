from django.urls import path

from emails import views

urlpatterns = [
    path(
        "templates/",
        views.EmailTemplateListView.as_view(),
        name="email_templates_list",
    ),
    path(
        "scheduled_emails/",
        views.ScheduledEmailListView.as_view(),
        name="scheduled_emails_list",
    ),
]
