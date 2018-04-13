from django.conf.urls import url, include
from django.views.generic import RedirectView

from workshops import views

urlpatterns = [
    url(r'^$', views.dispatch, name='dispatch'),
    url(r'^admin-dashboard/$', views.admin_dashboard, name='admin-dashboard'),
    url(r'^trainee-dashboard/$', views.trainee_dashboard, name='trainee-dashboard'),

    url(r'^log/$', views.changes_log, name='changes_log'),

    url(r'^organizations/', include([
        url(r'^$', views.AllOrganizations.as_view(), name='all_organizations'),
        url(r'^add/$', views.OrganizationCreate.as_view(), name='organization_add'),
    ])),
    url(r'^organization/(?P<org_domain>[\w\.-]+)/', include([
        url(r'^$', views.OrganizationDetails.as_view(), name='organization_details'),
        url(r'^edit/$', views.OrganizationUpdate.as_view(), name='organization_edit'),
        url(r'^delete/$', views.OrganizationDelete.as_view(), name='organization_delete'),
    ])),

    url(r'^memberships/', include([
        url(r'^$', views.AllMemberships.as_view(), name='all_memberships'),
        url(r'^add/$', views.MembershipCreate.as_view(), name='membership_add'),
    ])),
    url(r'^membership/(?P<membership_id>\d+)/', include([
        url(r'^$', views.MembershipDetails.as_view(), name='membership_details'),
        url(r'^edit/$', views.MembershipUpdate.as_view(), name='membership_edit'),
        url(r'^delete/$', views.MembershipDelete.as_view(), name='membership_delete'),
    ])),

    url(r'^airports/', include([
        url(r'^$', views.AllAirports.as_view(), name='all_airports'),
        url(r'^add/$', views.AirportCreate.as_view(), name='airport_add'),
    ])),
    url(r'^airport/(?P<airport_iata>\w+)/', include([
        url(r'^$', views.AirportDetails.as_view(), name='airport_details'),
        url(r'^edit/$', views.AirportUpdate.as_view(), name='airport_edit'),
        url(r'^delete/$', views.AirportDelete.as_view(), name='airport_delete'),
    ])),

    url(r'^bulk_upload/', include([
        url(r'^$',views.person_bulk_add, name='person_bulk_add'),
        url(r'^template/$',views.person_bulk_add_template, name='person_bulk_add_template'),
        url(r'^confirm/$',views.person_bulk_add_confirmation, name='person_bulk_add_confirmation'),
        url(r'^(?P<entry_id>\d+)/remove/$',views.person_bulk_add_remove_entry, name='person_bulk_add_remove_entry'),
        url(r'^(?P<entry_id>\d+)/match_person/(?P<person_id>\d+)$',views.person_bulk_add_match_person, name='person_bulk_add_match_person'),
    ])),

    url(r'^persons/', include([
        url(r'^$', views.AllPersons.as_view(), name='all_persons'),
        url(r'^add/$', views.PersonCreate.as_view(), name='person_add'),
        url(r'^merge/$', views.persons_merge, name='persons_merge'),
    ])),
    url(r'^person/(?P<person_id>\d+)/', include([
        url(r'^$', views.PersonDetails.as_view(), name='person_details'),
        url(r'^edit/$', views.PersonUpdate.as_view(), name='person_edit'),
        url(r'^delete/$', views.PersonDelete.as_view(), name='person_delete'),
        url(r'^permissions/$', views.PersonPermissions.as_view(), name='person_permissions'),
        url(r'^password/$', views.person_password, name='person_password'),
        url(r'^sync_usersocialauth/$', views.sync_usersocialauth, name='sync_usersocialauth'),
    ])),

    url(r'^events/', include([
        url(r'^$', views.AllEvents.as_view(), name='all_events'),
        url(r'^add/$', views.EventCreate.as_view(), name='event_add'),
        url(r'^import/$', views.event_import, name='event_import'),
        url(r'^merge/$', views.events_merge, name='events_merge'),
        url(r'^metadata_changed/$', views.events_metadata_changed, name='events_metadata_changed'),
    ])),
    url(r'^event/(?P<slug>[\w-]+)/', include([
        url(r'^$', views.event_details, name='event_details'),
        url(r'^assign/$', views.event_assign, name='event_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', views.event_assign, name='event_assign'),
        url(r'^edit/$', views.EventUpdate.as_view(), name='event_edit'),
        url(r'^delete/$', views.EventDelete.as_view(), name='event_delete'),
        url(r'^validate/$', views.validate_event, name='validate_event'),
        url(r'^review_metadata_changes/$', views.event_review_metadata_changes, name='event_review_metadata_changes'),
        url(r'^review_metadata_changes/accept/$', views.event_accept_metadata_changes, name='event_accept_metadata_changes'),
        url(r'^review_metadata_changes/dismiss/$', views.event_dismiss_metadata_changes, name='event_dismiss_metadata_changes'),
        url(r'^invoice/$', views.event_invoice, name='event_invoice'),
    ])),

    url(r'^invoices/$', views.AllInvoiceRequests.as_view(), name='all_invoicerequests'),
    url(r'^invoice/(?P<request_id>\d+)/', include([
        url(r'^$', views.InvoiceRequestDetails.as_view(), name='invoicerequest_details'),
        url(r'^edit/$', views.InvoiceRequestUpdate.as_view(), name='invoicerequest_edit'),
    ])),

    url(r'^tasks/', include([
        url(r'^$', views.AllTasks.as_view(), name='all_tasks'),
        url(r'^add/$', views.TaskCreate.as_view(), name='task_add'),
    ])),
    url(r'^task/(?P<task_id>\d+)/', include([
        url(r'^$', views.task_details, name='task_details'),
        url(r'^edit/$', views.TaskUpdate.as_view(), name='task_edit'),
        url(r'^delete/$', views.TaskDelete.as_view(), name='task_delete'),
    ])),

    url(r'^sponsorships/add/$', views.SponsorshipCreate.as_view(), name='sponsorship_add'),
    url(r'^sponsorship/(?P<pk>\d+)/delete/$', views.SponsorshipDelete.as_view(), name='sponsorship_delete'),

    url(r'^awards/add/$', views.AwardCreate.as_view(), name='award_add'),
    url(r'^award/(?P<pk>\d+)/', include([
        url(r'download/$', views.AwardCertification.as_view(), name='award_certificate'),
        url(r'delete/$', views.AwardDelete.as_view(), name='award_delete'),
    ])),

    url(r'^badges/$', views.AllBadges.as_view(), name='all_badges'),
    url(r'^badge/(?P<badge_name>[\w\.=-]+)/$', views.BadgeDetails.as_view(), name='badge_details'),

    url(r'^trainings/$', views.AllTrainings.as_view(), name='all_trainings'),

    url(r'^workshop_staff/$', views.workshop_staff, name='workshop_staff'),

    url(r'^search/$', views.search, name='search'),

    url(r'^instructors_by_date/$', views.instructors_by_date, name='instructors_by_date'),

    url(r'^export/', include([
        url(r'^badges/$', views.export_badges, name='export_badges'),
        url(r'^instructors/$', views.export_instructors, name='export_instructors'),
        url(r'^members/$', views.export_members, name='export_members'),
    ])),

    url(r'^reports/', include([
        url(r'^workshops_over_time/$', views.workshops_over_time, name='workshops_over_time'),
        url(r'^learners_over_time/$', views.learners_over_time, name='learners_over_time'),
        url(r'^instructors_over_time/$', views.instructors_over_time, name='instructors_over_time'),
        url(r'^instructor_num_taught/$', views.instructor_num_taught, name='instructor_num_taught'),
        url(r'^all_activity_over_time/$', views.all_activity_over_time, name='all_activity_over_time'),
        url(r'^workshop_issues/$', views.workshop_issues, name='workshop_issues'),
        url(r'^instructor_issues/$', views.instructor_issues, name='instructor_issues'),
        url(r'^duplicates/$', views.duplicates, name='duplicates'),
    ])),

    url(r'^version/(?P<version_id>[\d]+)/$', views.object_changes, name='object_changes'),

    url(r'^requests/$', views.AllEventRequests.as_view(), name='all_eventrequests'),
    url(r'^request/(?P<request_id>\d+)/', include([
        url(r'^$', views.EventRequestDetails.as_view(), name='eventrequest_details'),
        url(r'^discard/$', views.eventrequest_discard, name='eventrequest_discard'),
        url(r'^accept/$', views.eventrequest_accept, name='eventrequest_accept'),
        url(r'^assign/$', views.eventrequest_assign, name='eventrequest_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', views.eventrequest_assign, name='eventrequest_assign'),
    ])),
    url(r'^dc_selforganized_requests/$', views.AllDCSelfOrganizedEventRequests.as_view(), name='all_dcselforganizedeventrequests'),
    url(r'^dc_selforganized_request/(?P<request_id>\d+)/', include([
        url(r'^$', views.DCSelfOrganizedEventRequestDetails.as_view(), name='dcselforganizedeventrequest_details'),
        url(r'^edit/$', views.DCSelfOrganizedEventRequestChange.as_view(), name='dcselforganizedeventrequest_edit'),
        url(r'^assign/$', views.dcselforganizedeventrequest_assign, name='dcselforganizedeventrequest_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', views.dcselforganizedeventrequest_assign, name='dcselforganizedeventrequest_assign'),
    ])),

    url(r'^submissions/$', views.AllEventSubmissions.as_view(), name='all_eventsubmissions'),
    url(r'^submission/(?P<submission_id>\d+)/', include([
        url(r'^$', views.EventSubmissionDetails.as_view(), name='eventsubmission_details'),
        url(r'^fix/$', views.EventSubmissionFix.as_view(), name='eventsubmission_fix'),
        url(r'^discard/$', views.eventsubmission_discard, name='eventsubmission_discard'),
        url(r'^accept/$', views.eventsubmission_accept, name='eventsubmission_accept'),
        url(r'^assign/$', views.eventsubmission_assign, name='eventsubmission_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', views.eventsubmission_assign, name='eventsubmission_assign'),
    ])),

    url(r'^profile_updates/$', views.AllProfileUpdateRequests.as_view(), name='all_profileupdaterequests'),
    url(r'^profile_updates/closed/$', views.AllClosedProfileUpdateRequests.as_view(), name='all_closed_profileupdaterequests'),
    url(r'^profile_update/(?P<request_id>\d+)/', include([
        url(r'^$', views.profileupdaterequest_details, name='profileupdaterequest_details'),
        url(r'^fix/$', views.ProfileUpdateRequestFix.as_view(), name='profileupdaterequest_fix'),
        url(r'^discard/$', views.profileupdaterequest_discard, name='profileupdaterequest_discard'),
        url(r'^accept/$', views.profileupdaterequest_accept, name='profileupdaterequest_accept'),
        url(r'^accept/(?P<person_id>[\w\.-]+)/$', views.profileupdaterequest_accept, name='profileupdaterequest_accept'),
    ])),
    url(r'^autoupdate_profile/$', views.autoupdate_profile, name='autoupdate_profile'),

    url(r'^training_requests/$', views.all_trainingrequests, name='all_trainingrequests'),
    url(r'^training_requests/csv/$', views.download_trainingrequests, name='download_trainingrequests'),
    url(r'^training_request/(?P<pk>\d+)/', include([
        url(r'^$', views.trainingrequest_details, name='trainingrequest_details'),
        url(r'^edit/$', views.TrainingRequestUpdate.as_view(), name='trainingrequest_edit'),
    ])),

    url(r'^trainees/$', views.all_trainees, name='all_trainees'),

    url(r'^training_progresses/add/$', views.TrainingProgressCreate.as_view(), name='trainingprogress_add'),
    url(r'^training_progress/(?P<pk>\d+)/', include([
        url(r'^edit/$', views.TrainingProgressUpdate.as_view(), name='trainingprogress_edit'),
        url(r'^delete/$', views.TrainingProgressDelete.as_view(), name='trainingprogress_delete'),
    ])),

    url(r'^todos/(?P<slug>[\w-]+)/add/$', views.todos_add, name='todos_add'),
    url(r'^todo/(?P<todo_id>\d+)/', include([
        url(r'^completed/$', views.todo_mark_completed, name='todo_mark_completed'),
        url(r'^incompleted/$', views.todo_mark_incompleted, name='todo_mark_incompleted'),
        url(r'^edit/$', views.TodoItemUpdate.as_view(), name='todo_edit'),
        url(r'^delete/$', views.TodoDelete.as_view(), name='todo_delete'),
    ])),

    # redirects for the old forms
    url(r'^swc/request/$',
        RedirectView.as_view(pattern_name='swc_workshop_request', permanent=True),
        name='old_swc_workshop_request'),
    url(r'^swc/request/confirm/$',
        RedirectView.as_view(pattern_name='swc_workshop_request_confirm', permanent=True),
        name='old_swc_workshop_request_confirm'),
    url(r'^dc/request/$',
        RedirectView.as_view(pattern_name='dc_workshop_request', permanent=True),
        name='old_dc_workshop_request'),
    url(r'^dc/request/confirm/$',
        RedirectView.as_view(pattern_name='dc_workshop_request_confirm', permanent=True),
        name='old_dc_workshop_request_confirm'),
    url(r'^dc/request_selforganized/$',
        RedirectView.as_view(pattern_name='dc_workshop_selforganized_request', permanent=True),
        name='old_dc_workshop_selforganized_request'),
    url(r'^dc/request_selforganized/confirm/$',
        RedirectView.as_view(pattern_name='dc_workshop_selforganized_request_confirm', permanent=True),
        name='old_dc_workshop_selforganized_request_confirm'),
    url(r'^submit/$',
        RedirectView.as_view(pattern_name='event_submit', permanent=True),
        name='old_event_submit'),
    # url(r'^submit/confirm/$',
    #     RedirectView.as_view(pattern_name='event_submission_confirm', permanent=True),
    #     name='old_event_submission_confirm'),
    url(r'^update_profile/$',
        RedirectView.as_view(pattern_name='profileupdate_request', permanent=True),
        name='old_profileupdate_request'),
    url(r'^request_training/$',
        RedirectView.as_view(pattern_name='training_request', permanent=True),
        name='old_training_request'),
]
