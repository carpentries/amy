from django.urls import path

from reports import views

urlpatterns = [
    path('instructors_by_date/', views.instructors_by_date, name='instructors_by_date'),
    path('workshops_over_time/', views.workshops_over_time, name='workshops_over_time'),
    path('learners_over_time/', views.learners_over_time, name='learners_over_time'),
    path('instructors_over_time/', views.instructors_over_time, name='instructors_over_time'),
    path('instructor_num_taught/', views.instructor_num_taught, name='instructor_num_taught'),
    path('all_activity_over_time/', views.all_activity_over_time, name='all_activity_over_time'),
    path('membership_trainings_stats/', views.membership_trainings_stats, name='membership_trainings_stats'),
    path('workshop_issues/', views.workshop_issues, name='workshop_issues'),
    path('instructor_issues/', views.instructor_issues, name='instructor_issues'),
    path('duplicate_persons/', views.duplicate_persons, name='duplicate_persons'),
    path('duplicate_training_requests/', views.duplicate_training_requests, name='duplicate_training_requests'),
]
