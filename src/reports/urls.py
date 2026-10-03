from django.urls import path

from src.reports import views

urlpatterns = [
    path("membership_trainings_stats/", views.MembershipTrainingsStats.as_view(), name="membership_trainings_stats"),
    path("workshop_issues/", views.WorkshopIssues.as_view(), name="workshop_issues"),
    path("instructor_issues/", views.InstructorIssues.as_view(), name="instructor_issues"),
    path("duplicate_persons/", views.DuplicatePersons.as_view(), name="duplicate_persons"),
    path("duplicate_persons/review/", views.ReviewDuplicatePersons.as_view(), name="review_duplicate_persons"),
    path("duplicate_training_requests/", views.DuplicateTrainingRequests.as_view(), name="duplicate_training_requests"),
]
