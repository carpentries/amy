from django.conf.urls import url
from .views import AirportCreate, AirportUpdate, \
                   PersonCreate, PersonUpdate, \
                   SiteCreate, SiteUpdate, \
                   TaskCreate, TaskUpdate, \
                   CohortCreate, CohortUpdate, \
                   match

from workshops import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^sites/?$', views.all_sites, name='all_sites'),
    url(r'^site/(?P<site_domain>[\w\.-]+)/?$', views.site_details, name='site_details'),
    url(r'^site/(?P<site_domain>[\w\.-]+)/edit$', SiteUpdate.as_view(), name='site_edit'),
    url(r'^sites/add/$', SiteCreate.as_view(), name='site_add'),

    url(r'^airports/?$', views.all_airports, name='all_airports'),
    url(r'^airport/(?P<airport_iata>[\w\.-]+)/?$', views.airport_details, name='airport_details'),
    url(r'^airport/(?P<airport_iata>[\w\.-]+)/edit$', AirportUpdate.as_view(), name='airport_edit'),
    url(r'^airports/add/$', AirportCreate.as_view(), name='airport_add'),

    url(r'^persons/?$', views.all_persons, name='all_persons'),
    url(r'^person/(?P<person_id>[\w\.-]+)/?$', views.person_details, name='person_details'),
    url(r'^person/(?P<person_id>[\w\.-]+)/edit$', PersonUpdate.as_view(), name='person_edit'),
    url(r'^persons/add/$', PersonCreate.as_view(), name='person_add'),

    url(r'^events/?$', views.all_events, name='all_events'),
    url(r'^event/(?P<event_slug>[\w\.-]+)/?$', views.event_details, name='event_details'),
    url(r'^event/(?P<event_slug>[\w\.-]+)/validate/?$', views.validate_event, name='validate_event'),

    url(r'^tasks/?$', views.all_tasks, name='all_tasks'),
    url(r'^task/(?P<event_slug>[\w\.-]+)/(?P<person_id>[\w\.-]+)/(?P<role_name>[\w\.-]+)/?$', views.task_details, name='task_details'),
    url(r'^task/(?P<event_slug>[\w\.-]+)/(?P<person_id>[\w\.-]+)/(?P<role_name>[\w\.-]+)/edit$', TaskUpdate.as_view(), name='task_edit'),
    url(r'^tasks/add/$', TaskCreate.as_view(), name='task_add'),

    url(r'^cohorts/?$', views.all_cohorts, name='all_cohorts'),
    url(r'^cohort/(?P<cohort_name>[\w\.-]+)/?$', views.cohort_details, name='cohort_details'),
    url(r'^cohort/(?P<cohort_name>[\w\.-]+)/edit$', CohortUpdate.as_view(), name='cohort_edit'),
    url(r'^cohorts/add/$', CohortCreate.as_view(), name='cohort_add'),

    url(r'^badges/?$', views.all_badges, name='all_badges'),
    url(r'^badge/(?P<badge_name>[\w\.-]+)/?$', views.badge_details, name='badge_details'),

    url(r'^export/(?P<name>[\w\.-]+)/?$', views.export, name='export'),

    url(r'^match/?$', views.match, name='match'),

    url(r'^search/?$', views.search, name='search'),
]
