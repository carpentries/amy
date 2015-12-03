from django.conf.urls import url
from workshops import views

urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),

    url(r'^log/$', views.changes_log, name='changes_log'),

    url(r'^hosts/?$', views.all_hosts, name='all_hosts'),
    url(r'^host/(?P<host_domain>[\w\.-]+)/?$', views.host_details, name='host_details'),
    url(r'^host/(?P<host_domain>[\w\.-]+)/edit$', views.HostUpdate.as_view(), name='host_edit'),
    url(r'^host/(?P<host_domain>[\w\.-]+)/delete$', views.host_delete, name='host_delete'),
    url(r'^hosts/add/$', views.HostCreate.as_view(), name='host_add'),

    url(r'membership/(?P<host_domain>[\w\.-]+)/add', views.membership_create, name='membership_add'),
    url(r'membership/(?P<membership_id>\d+)/edit', views.MembershipUpdate.as_view(), name='membership_edit'),

    url(r'^airports/?$', views.all_airports, name='all_airports'),
    url(r'^airport/(?P<airport_iata>\w+)/?$', views.airport_details, name='airport_details'),
    url(r'^airport/(?P<airport_iata>\w+)/edit$', views.AirportUpdate.as_view(), name='airport_edit'),
    url(r'^airport/(?P<airport_iata>\w+)/delete$', views.airport_delete, name='airport_delete'),
    url(r'^airports/add/$', views.AirportCreate.as_view(), name='airport_add'),

    url(r'^persons/?$', views.all_persons, name='all_persons'),
    url(r'^person/(?P<person_id>[\w\.-]+)/?$', views.person_details, name='person_details'),
    url(r'^person/(?P<person_id>[\w\.-]+)/edit$', views.person_edit, name='person_edit'),
    url(r'^person/(?P<person_id>[\w\.-]+)/delete$', views.person_delete, name='person_delete'),
    url(r'^person/(?P<person_id>[\w\.-]+)/permissions$', views.PersonPermissions.as_view(), name='person_permissions'),
    url(r'^person/(?P<person_id>[\w\.-]+)/password$', views.person_password, name='person_password'),
    url(r'^persons/add/$', views.PersonCreate.as_view(), name='person_add'),
    url(r'^persons/bulkadd/$',views.person_bulk_add, name='person_bulk_add'),
    url(r'^persons/bulkadd/template',views.person_bulk_add_template, name='person_bulk_add_template'),
    url(r'^persons/bulkadd/confirm$',views.person_bulk_add_confirmation, name='person_bulk_add_confirmation'),
    url(r'^persons/merge/$',views.person_merge, name='person_merge'),
    url(r'^persons/merge/confirm$',views.person_merge_confirmation, name='person_merge_confirmation'),

    url(r'^events/?$', views.all_events, name='all_events'),
    url(r'^event/(?P<event_ident>[\w-]+)/?$', views.event_details, name='event_details'),
    url(r'^event/(?P<event_ident>[\w-]+)/assign$', views.event_assign, name='event_assign'),
    url(r'^event/(?P<event_ident>[\w-]+)/assign/(?P<person_id>[\w\.-]+)$', views.event_assign, name='event_assign'),
    url(r'^event/(?P<event_ident>[\w-]+)/edit$', views.event_edit, name='event_edit'),
    url(r'^event/(?P<event_ident>[\w-]+)/delete$', views.event_delete, name='event_delete'),
    url(r'^events/add/$', views.EventCreate.as_view(), name='event_add'),
    url(r'^event/(?P<event_ident>[\w-]+)/validate/?$', views.validate_event, name='validate_event'),
    url(r'^events/import/?$', views.event_import, name='event_import'),

    url(r'^tasks/?$', views.all_tasks, name='all_tasks'),
    url(r'^task/(?P<task_id>\d+)/?$', views.task_details, name='task_details'),
    url(r'^task/(?P<task_id>\d+)/edit$', views.TaskUpdate.as_view(), name='task_edit'),
    url(r'^task/(?P<task_id>\d+)/delete$', views.task_delete, name='task_delete'),
    url(r'^event/(?P<event_ident>[\w-]+)/task/(?P<task_id>\d+)/delete$', views.task_delete, name='task_delete'),
    url(r'^tasks/add/$', views.TaskCreate.as_view(), name='task_add'),

    url(r'^award/(?P<award_id>\d+)/delete$', views.award_delete, name='award_delete'),
    url(r'^person/(?P<person_id>[\w\.-]+)/award/(?P<award_id>\d+)/delete$', views.award_delete, name='award_delete'),

    url(r'^badges/?$', views.all_badges, name='all_badges'),
    url(r'^badge/(?P<badge_name>[\w\.=-]+)/?$', views.badge_details, name='badge_details'),

    url(r'^instructors/?$', views.instructors, name='instructors'),

    url(r'^search/?$', views.search, name='search'),

    url(r'^debrief/?$', views.debrief, name='debrief'),

    url(r'^export/badges/?$', views.export_badges, name='export_badges'),
    url(r'^export/instructors/?$', views.export_instructors, name='export_instructors'),
    url(r'^export/members/?$', views.export_members, name='export_members'),

    url(r'^reports/workshops_over_time/?$', views.workshops_over_time, name='workshops_over_time'),
    url(r'^reports/learners_over_time/?$', views.learners_over_time, name='learners_over_time'),
    url(r'^reports/instructors_over_time/?$', views.instructors_over_time, name='instructors_over_time'),
    url(r'^reports/instructor_num_taught/?$', views.instructor_num_taught, name='instructor_num_taught'),
    url(r'^reports/workshop_issues/?$', views.workshop_issues, name='workshop_issues'),
    url(r'^reports/instructor_issues/?$', views.instructor_issues, name='instructor_issues'),

    url(r'^revision/(?P<revision_id>[\d]+)/?$', views.object_changes, name='object_changes'),

    url(r'^requests/$', views.all_eventrequests, name='all_eventrequests'),
    url(r'^request/(?P<request_id>\d+)/?$', views.EventRequestDetails.as_view(), name='eventrequest_details'),
    url(r'^request/(?P<request_id>\d+)/discard/?$', views.eventrequest_discard, name='eventrequest_discard'),
    url(r'^request/(?P<request_id>\d+)/accept/?$', views.eventrequest_accept, name='eventrequest_accept'),
    url(r'^request/(?P<request_id>\d+)/assign$', views.eventrequest_assign, name='eventrequest_assign'),
    url(r'^request/(?P<request_id>\d+)/assign/(?P<person_id>[\w\.-]+)$', views.eventrequest_assign, name='eventrequest_assign'),
    url(r'^swc/request/$', views.SWCEventRequest.as_view(), name='swc_workshop_request'),
    url(r'^dc/request/$', views.DCEventRequest.as_view(), name='dc_workshop_request'),

    url(r'^profile_updates/$', views.AllProfileUpdateRequests.as_view(), name='all_profileupdaterequests'),
    url(r'^profile_updates/closed/$', views.AllClosedProfileUpdateRequests.as_view(), name='all_closed_profileupdaterequests'),
    url(r'^profile_update/(?P<request_id>\d+)/?$', views.profileupdaterequest_details, name='profileupdaterequest_details'),
    url(r'^profile_update/(?P<request_id>\d+)/fix/?$', views.ProfileUpdateRequestFix.as_view(), name='profileupdaterequest_fix'),
    url(r'^profile_update/(?P<request_id>\d+)/discard/?$', views.profileupdaterequest_discard, name='profileupdaterequest_discard'),
    url(r'^profile_update/(?P<request_id>\d+)/accept/(?P<person_id>[\w\.-]+)/?$', views.profileupdaterequest_accept, name='profileupdaterequest_accept'),
    url(r'^update_profile/$', views.profileupdaterequest_create, name='profileupdate_request'),

    url(r'^todos/(?P<event_ident>[\w-]+)/add$', views.todos_add, name='todos_add'),
    url(r'^todo/(?P<todo_id>\d+)/completed', views.todo_mark_completed, name='todo_mark_completed'),
    url(r'^todo/(?P<todo_id>\d+)/incompleted', views.todo_mark_incompleted, name='todo_mark_incompleted'),
    url(r'^todo/(?P<todo_id>\d+)/edit', views.TodoItemUpdate.as_view(), name='todo_edit'),
    url(r'^todo/(?P<todo_id>\d+)/delete', views.todo_delete, name='todo_delete'),
]
