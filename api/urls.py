from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    url('^$', views.ApiRoot.as_view()),
    url('^export/badges/$',
        views.ExportBadgesView.as_view(),
        name='export-badges'),
    url('^export/instructors/$',
        views.ExportInstructorLocationsView.as_view(),
        name='export-instructors'),
    url('^export/members/$',
        views.ExportMembersView.as_view(),
        name='export-members'),
    url('^events/published/$',
        views.PublishedEvents.as_view(),
        name='events-published'),
]

# for login-logout functionality
urlpatterns += [
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),
]

urlpatterns = format_suffix_patterns(urlpatterns)  # allow to specify format
