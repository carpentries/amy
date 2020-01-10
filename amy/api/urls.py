from django.urls import path, include
from rest_framework_nested import routers
from rest_framework.urlpatterns import format_suffix_patterns

from api import views

# new in Django 1.9: this defines a namespace for URLs; there's no need for
# `namespace='api'` in the include()
app_name = 'api'

# routers generate URLs for methods like `.list` or `.retrieve`
router = routers.SimpleRouter()
router.register('reports', views.ReportsViewSet, basename='reports')
router.register('persons', views.PersonViewSet)
awards_router = routers.NestedSimpleRouter(router, 'persons', lookup='person')
awards_router.register('awards', views.AwardViewSet, basename='person-awards')
person_task_router = routers.NestedSimpleRouter(router, 'persons',
                                                lookup='person')
person_task_router.register('tasks', views.PersonTaskViewSet,
                            basename='person-tasks')
router.register('events', views.EventViewSet)
tasks_router = routers.NestedSimpleRouter(router, 'events', lookup='event')
tasks_router.register('tasks', views.TaskViewSet, basename='event-tasks')
router.register('organizations', views.OrganizationViewSet)
router.register('airports', views.AirportViewSet)

urlpatterns = [
    path('', views.ApiRoot.as_view(), name='root'),
    # TODO: turn these export views into ViewSets and add them to the router
    path('export/badges/',
         views.ExportBadgesView.as_view(),
         name='export-badges'),
    path('export/badges_by_person/',
         views.ExportBadgesByPersonView.as_view(),
         name='export-badges-by-person'),
    path('export/instructors/',
         views.ExportInstructorLocationsView.as_view(),
         name='export-instructors'),
    path('export/members/',
         views.ExportMembersView.as_view(),
         name='export-members'),
    path('export/person_data/',
         views.ExportPersonDataView.as_view(),
         name='export-person-data'),
    path('events/published/',
         views.PublishedEvents.as_view(),
         name='events-published'),
    path('training_requests/',
         views.TrainingRequests.as_view(),
         name='training-requests'),

    path('', include(router.urls)),
    path('', include(awards_router.urls)),
    path('', include(person_task_router.urls)),
    path('', include(tasks_router.urls)),
]

urlpatterns = format_suffix_patterns(urlpatterns)  # allow to specify format
