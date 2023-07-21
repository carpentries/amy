from django.urls import include, path

from emails import views

urlpatterns = [
    path(
        "templates/",
        include([
            path(
                "",
                views.AllEmailTemplates.as_view(),
                name="all_emailtemplates",
            ),
            path(
                "create/",
                views.EmailTemplateCreate.as_view(),
                name="emailtemplate_add",
            ),
        ]),
    ),
    path(
        "template/<uuid:pk>/",
        include([
            path(
                "",
                views.EmailTemplateDetails.as_view(),
                name="emailtemplate_details",
            ),
            path(
                "edit/",
                views.EmailTemplateUpdate.as_view(),
                name="emailtemplate_edit",
            ),
            path(
                "delete/",
                views.EmailTemplateDelete.as_view(),
                name="emailtemplate_delete",
            ),
        ]),
    ),
    path(
        "scheduled_emails/",
        views.AllScheduledEmails.as_view(),
        name="all_scheduledemails",
    ),
    path("scheduled_email/<uuid:pk>/", include([
        path(
            "",
            views.ScheduledEmailDetails.as_view(),
            name="scheduledemail_details",
        ),
        path(
            "edit/",
            views.ScheduledEmailUpdate.as_view(),
            name="scheduledemail_edit",
        ),
        path(
            "reschedule/",
            views.ScheduledEmailReschedule.as_view(),
            name="scheduledemail_reschedule",
        ),
        path(
            "cancel/",
            views.ScheduledEmailCancel.as_view(),
            name="scheduledemail_cancel",
        ),
    ])),
]
