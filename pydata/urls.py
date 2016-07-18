from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^persons/import/?$', views.PersonImport.as_view(), name='person_import'),
    url(r'^events/import/?$', views.ConferenceImport.as_view(), name='event_import'),
    url(r'^tasks/import/?$', views.TaskImport.as_view(), name='task_import'),
    url(r'^sponsors/import/?$', views.SponsorImport.as_view(), name='sponsor_import'),
]
