from django.conf.urls import url, include
from rest_framework_nested import routers
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

# routers generate URLs for methods like `.list` or `.retrieve`
router = routers.SimpleRouter()
router.register('reports', views.ReportsViewSet, base_name='reports')
router.register('persons', views.PersonViewSet)
awards_router = routers.NestedSimpleRouter(router, 'persons', lookup='person')
awards_router.register('awards', views.AwardViewSet, base_name='person-awards')
router.register('events', views.EventViewSet)
tasks_router = routers.NestedSimpleRouter(router, 'events', lookup='event')
tasks_router.register('tasks', views.TaskViewSet, base_name='event-tasks')
todos_router = routers.NestedSimpleRouter(router, 'events', lookup='event')
todos_router.register('todos', views.TodoViewSet, base_name='event-todos')
router.register('hosts', views.HostViewSet)
router.register('airports', views.AirportViewSet)

urlpatterns = [
    url('^$', views.ApiRoot.as_view(), name='root'),
    # TODO: turn these export views into ViewSets and add them to the router
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
    url('^todos/user/$',
        views.UserTodoItems.as_view(),
        name='user-todos'),

    url('^', include(router.urls)),
    url('^', include(awards_router.urls)),
    url('^', include(tasks_router.urls)),
    url('^', include(todos_router.urls)),
]

# for login-logout functionality
urlpatterns += [
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),
]

urlpatterns = format_suffix_patterns(urlpatterns)  # allow to specify format
