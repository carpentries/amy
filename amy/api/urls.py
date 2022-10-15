from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework_nested import routers

from api import views

app_name = "api"

# routers generate URLs for methods like `.list` or `.retrieve`
router = routers.SimpleRouter(trailing_slash=False)
router.register("persons", views.PersonViewSet)
awards_router = routers.NestedSimpleRouter(router, "persons", lookup="person")
awards_router.register("awards", views.AwardViewSet, basename="person-awards")
person_task_router = routers.NestedSimpleRouter(router, "persons", lookup="person")
person_task_router.register("tasks", views.PersonTaskViewSet, basename="person-tasks")
person_consent_router = routers.NestedSimpleRouter(router, "persons", lookup="person")
person_consent_router.register(
    "consents", views.PersonConsentViewSet, basename="person-consents"
)
training_progress_router = routers.NestedSimpleRouter(
    router, "persons", lookup="person"
)
training_progress_router.register(
    "trainingprogress",
    views.TrainingProgressViewSet,
    basename="person-training-progress",
)
router.register("events", views.EventViewSet)
tasks_router = routers.NestedSimpleRouter(router, "events", lookup="event")
tasks_router.register("tasks", views.TaskViewSet, basename="event-tasks")
router.register("organizations", views.OrganizationViewSet)
router.register("airports", views.AirportViewSet)
router.register("emailtemplates", views.EmailTemplateViewSet, basename="emailtemplate")
router.register("terms", views.TermViewSet)
router.register(
    "communityroleconfigs",
    views.CommunityRoleConfigViewSet,
    basename="communityroleconfig",
)
router.register(
    "instructorrecruitment",
    views.InstructorRecruitmentViewSet,
    basename="instructorrecruitment",
)

urlpatterns = [
    path("", views.ApiRoot.as_view(), name="root"),
    path(
        "export/person_data/",
        views.ExportPersonDataView.as_view(),
        name="export-person-data",
    ),
    path(
        "training_requests/", views.TrainingRequests.as_view(), name="training-requests"
    ),
    path("", include(router.urls)),
    path("", include(awards_router.urls)),
    path("", include(person_task_router.urls)),
    path("", include(person_consent_router.urls)),
    path("", include(tasks_router.urls)),
    path("", include(training_progress_router.urls)),
]

urlpatterns = format_suffix_patterns(urlpatterns)  # allow to specify format
