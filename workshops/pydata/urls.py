from django.conf.urls import url

from .views import ConferenceImport


urlpatterns = [
    url(r'^events/import/?$', ConferenceImport.as_view(), name='event_import'),
]
