from django.urls import path

from reports import views

urlpatterns = [
    path('membership_trainings_stats/', views.membership_trainings_stats, name='membership_trainings_stats'),
    path('workshop_issues/', views.workshop_issues, name='workshop_issues'),
    path('instructor_issues/', views.instructor_issues, name='instructor_issues'),
    path('duplicate_persons/', views.duplicate_persons, name='duplicate_persons'),
    path('duplicate_persons/review/', views.review_duplicate_persons, name='review_duplicate_persons'),
    path('duplicate_training_requests/', views.duplicate_training_requests, name='duplicate_training_requests'),
]
