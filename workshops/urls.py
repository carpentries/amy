from django.conf.urls import url
from workshops import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^sites/?$', views.all_sites, name='all_sites'),
    url(r'^site/(?P<site_domain>[\w\.-]+)/?$', views.site_details, name='site_details'),
    url(r'^site/(?P<site_domain>[\w\.-]+)/edit$', views.SiteUpdate.as_view(), name='site_edit'),
    url(r'^sites/add/$', views.SiteCreate.as_view(), name='site_add'),

    url(r'^airports/?$', views.all_airports, name='all_airports'),
    url(r'^airport/(?P<airport_iata>\w+)/?$', views.airport_details, name='airport_details'),
    url(r'^airport/(?P<airport_iata>\w+)/edit$', views.AirportUpdate.as_view(), name='airport_edit'),
    url(r'^airports/add/$', views.AirportCreate.as_view(), name='airport_add'),

    url(r'^persons/?$', views.all_persons, name='all_persons'),
    url(r'^person/(?P<person_id>[\w\.-]+)/?$', views.person_details, name='person_details'),
    url(r'^person/(?P<person_id>[\w\.-]+)/edit$', views.PersonUpdate.as_view(), name='person_edit'),
    url(r'^persons/add/$', views.PersonCreate.as_view(), name='person_add'),
    url(r'^persons/bulkadd/$',views.person_bulk_add, name='person_bulk_add'),
    url(r'^persons/bulkadd/confirm$',views.person_bulk_add_confirmation, name='person_bulk_add_confirmation'),

    url(r'^events/?$', views.all_events, name='all_events'),
    url(r'^event/(?P<event_ident>[\w-]+)/?$', views.event_details, name='event_details'),
    url(r'^event/(?P<event_ident>[\w-]+)/edit$', views.EventUpdate.as_view(), name='event_edit'),
    url(r'^events/add/$', views.EventCreate.as_view(), name='event_add'),
    url(r'^event/(?P<event_ident>[\w-]+)/validate/?$', views.validate_event, name='validate_event'),

    url(r'^tasks/?$', views.all_tasks, name='all_tasks'),
    url(r'^task/(?P<task_id>\d+)/?', views.task_details, name='task_details'),
    url(r'^task/(?P<task_id>\d+)/edit$', views.TaskUpdate.as_view(), name='task_edit'),
    url(r'^tasks/add/$', views.TaskCreate.as_view(), name='task_add'),

    url(r'^badges/?$', views.all_badges, name='all_badges'),
    url(r'^badge/(?P<badge_name>[\w\.-]+)/?$', views.badge_details, name='badge_details'),

    url(r'^instructors/?$', views.instructors, name='instructors'),

    url(r'^search/?$', views.search, name='search'),

    url(r'^export/(?P<name>[\w\.-]+)/?$', views.export, name='export'),
]
