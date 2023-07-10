from django.urls import include, path

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
    path("scheduled_email/<uuid:pk>/", include([
        path(
            "",
            views.ScheduledEmailDetailView.as_view(),
            name="scheduled_email_detail",
        ),
        path(
            "edit/",
            views.ScheduledEmailEditView.as_view(),
            name="scheduled_email_edit",
        ),
        path(
            "reschedule/",
            views.ScheduledEmailRescheduleView.as_view(),
            name="scheduled_email_reschedule",
        ),
        path(
            "cancel/",
            views.ScheduledEmailCancelView.as_view(),
            name="scheduled_email_cancel",
        ),
    ])),
]
