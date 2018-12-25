from django.urls import path, include

from workshops import views

urlpatterns = [
    # utility views
    path('search/', views.search, name='search'),
    path('log/', views.changes_log, name='changes_log'),
    path('version/<int:version_id>/', views.object_changes, name='object_changes'),
    path('workshop_staff/', views.workshop_staff, name='workshop_staff'),

    # airports
    path('airports/', include([
        path('', views.AllAirports.as_view(), name='all_airports'),
        path('add/', views.AirportCreate.as_view(), name='airport_add'),
    ])),
    path('airport/<str:airport_iata>/', include([
        path('', views.AirportDetails.as_view(), name='airport_details'),
        path('edit/', views.AirportUpdate.as_view(), name='airport_edit'),
        path('delete/', views.AirportDelete.as_view(), name='airport_delete'),
    ])),

    # persons
    path('persons/', include([
        path('', views.AllPersons.as_view(), name='all_persons'),
        path('add/', views.PersonCreate.as_view(), name='person_add'),
        path('merge/', views.persons_merge, name='persons_merge'),
        path('bulk_upload/', include([
            path('', views.person_bulk_add, name='person_bulk_add'),
            path('template/', views.person_bulk_add_template, name='person_bulk_add_template'),
            path('confirm/', views.person_bulk_add_confirmation, name='person_bulk_add_confirmation'),
            path('<int:entry_id>/remove/', views.person_bulk_add_remove_entry, name='person_bulk_add_remove_entry'),
            path('<int:entry_id>/match_person/<int:person_id>', views.person_bulk_add_match_person, name='person_bulk_add_match_person'),
            path('<int:entry_id>/match_person/', views.person_bulk_add_match_person, name='person_bulk_add_match_person'),
        ])),
    ])),
    path('person/<int:person_id>/', include([
        path('', views.PersonDetails.as_view(), name='person_details'),
        path('edit/', views.PersonUpdate.as_view(), name='person_edit'),
        path('delete/', views.PersonDelete.as_view(), name='person_delete'),
        path('permissions/', views.PersonPermissions.as_view(), name='person_permissions'),
        path('password/', views.person_password, name='person_password'),
        path('sync_usersocialauth/', views.sync_usersocialauth, name='sync_usersocialauth'),
    ])),

    # events
    path('events/', include([
        path('', views.AllEvents.as_view(), name='all_events'),
        path('add/', views.EventCreate.as_view(), name='event_add'),
        path('import/', views.event_import, name='event_import'),
        path('merge/', views.events_merge, name='events_merge'),
        path('metadata_changed/', views.events_metadata_changed, name='events_metadata_changed'),
    ])),
    path('event/<slug:slug>/', include([
        path('', views.event_details, name='event_details'),
        path('assign/', views.EventAssign.as_view(), name='event_assign'),
        path('assign/<int:person_id>/', views.EventAssign.as_view(), name='event_assign'),
        path('edit/', views.EventUpdate.as_view(), name='event_edit'),
        path('delete/', views.EventDelete.as_view(), name='event_delete'),
        path('validate/', views.validate_event, name='validate_event'),
        path('review_metadata_changes/', views.event_review_metadata_changes, name='event_review_metadata_changes'),
        path('review_metadata_changes/accept/', views.event_accept_metadata_changes, name='event_accept_metadata_changes'),
        path('review_metadata_changes/dismiss/', views.event_dismiss_metadata_changes, name='event_dismiss_metadata_changes'),
    ])),

    # tasks
    path('tasks/', include([
        path('', views.AllTasks.as_view(), name='all_tasks'),
        path('add/', views.TaskCreate.as_view(), name='task_add'),
    ])),
    path('task/<int:task_id>/', include([
        path('', views.task_details, name='task_details'),
        path('edit/', views.TaskUpdate.as_view(), name='task_edit'),
        path('delete/', views.TaskDelete.as_view(), name='task_delete'),
    ])),

    # awards
    path('awards/add/', views.AwardCreate.as_view(), name='award_add'),
    path('award/<int:pk>/delete/', views.AwardDelete.as_view(), name='award_delete'),

    # badges
    path('badges/', views.AllBadges.as_view(), name='all_badges'),
    path('badge/<slug:badge_name>/', views.BadgeDetails.as_view(), name='badge_details'),

    # exporting views
    path('export/', include([
        path('badges/', views.export_badges, name='export_badges'),
        path('instructors/', views.export_instructors, name='export_instructors'),
        path('members/', views.export_members, name='export_members'),
    ])),

    # action-required views
    path('action_required/privacy/',
         views.action_required_privacy, name='action_required_privacy'),
]
