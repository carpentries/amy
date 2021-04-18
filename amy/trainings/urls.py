from django.urls import include, path

from trainings import views

urlpatterns = [
    # utility views
    path('trainings/', views.AllTrainings.as_view(), name='all_trainings'),
    path('trainees/', views.all_trainees, name='all_trainees'),
    # training progresses
    path('training_progresses/add/', views.TrainingProgressCreate.as_view(), name='trainingprogress_add'),
    path('training_progress/<int:pk>/', include([
        path('edit/', views.TrainingProgressUpdate.as_view(), name='trainingprogress_edit'),
        path('delete/', views.TrainingProgressDelete.as_view(), name='trainingprogress_delete'),
    ])),
]
