from django.conf.urls import url, include

from trainings import views

urlpatterns = [
    # utility views
    url(r'^trainings/$', views.AllTrainings.as_view(), name='all_trainings'),
    url(r'^trainees/$', views.all_trainees, name='all_trainees'),
    # training progresses
    url(r'^training_progresses/add/$', views.TrainingProgressCreate.as_view(), name='trainingprogress_add'),
    url(r'^training_progress/(?P<pk>\d+)/', include([
        url(r'^edit/$', views.TrainingProgressUpdate.as_view(), name='trainingprogress_edit'),
        url(r'^delete/$', views.TrainingProgressDelete.as_view(), name='trainingprogress_delete'),
    ])),
]
