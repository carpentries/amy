from django.urls import include, path
from rest_framework import routers

from api.v2 import views

app_name = "api-v2"

router = routers.DefaultRouter(trailing_slash=False)
router.register("award", views.AwardViewSet)
router.register("organization", views.OrganizationViewSet)
router.register("event", views.EventViewSet)
router.register("instructorrecruitmentsignup", views.InstructorRecruitmentSignupViewSet)
router.register("membership", views.MembershipViewSet)
router.register("person", views.PersonViewSet)
router.register("scheduledemail", views.ScheduledEmailViewSet)
router.register("task", views.TaskViewSet)
router.register("trainingprogress", views.TrainingProgressViewSet)
router.register("trainingrequirement", views.TrainingRequirementViewSet)
router.register("selforganisedsubmission", views.SelfOrganisedSubmissionViewSet)


urlpatterns = [
    path("", include(router.urls)),
]
