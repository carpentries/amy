from django.urls import path

from emails import views

urlpatterns = [
    path(
        "templates/",
        views.EmailTemplateListView.as_view(),
        name="email_templates_list",
    ),
    path(
        "template/<uuid:pk>/",
        views.EmailTemplateDetailView.as_view(),
        name="email_template_detail",
    ),
    path(
        "scheduled_emails/",
        views.ScheduledEmailListView.as_view(),
        name="scheduled_emails_list",
    ),
    path(
        "scheduled_email/<uuid:pk>/",
        views.ScheduledEmailDetailView.as_view(),
        name="scheduled_email_detail",
    ),
]
