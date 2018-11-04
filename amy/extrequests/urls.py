from django.conf.urls import url, include

from extrequests import views, deprecated_views


urlpatterns = [
    # training requests
    url(r'^training_requests/$', views.all_trainingrequests, name='all_trainingrequests'),
    url(r'^training_requests/merge$', views.trainingrequests_merge, name='trainingrequests_merge'),
    url(r'^training_request/(?P<pk>\d+)/', include([
        url(r'^$', views.trainingrequest_details, name='trainingrequest_details'),
        url(r'^edit/$', views.TrainingRequestUpdate.as_view(), name='trainingrequest_edit'),
    ])),
    url(r'^bulk_upload_training_request_scores/', views.bulk_upload_training_request_scores, name='bulk_upload_training_request_scores'),
    url(r'^bulk_upload_training_request_scores/confirm/$',views.bulk_upload_training_request_scores_confirmation, name='bulk_upload_training_request_scores_confirmation'),

    # unified workshop requests
    url(r'^workshop_requests/$', views.AllWorkshopRequests.as_view(), name='all_workshoprequests'),
    url(r'^workshop_request/(?P<request_id>\d+)/', include([
        url(r'^$', views.WorkshopRequestDetails.as_view(), name='workshoprequest_details'),
        url(r'^set_state/(?P<state>[\w]+)/$', views.WorkshopRequestSetState.as_view(), name='workshoprequest_set_state'),
        url(r'^accept_event/$', views.workshoprequest_accept_event, name='workshoprequest_accept_event'),
        url(r'^edit/$', views.WorkshopRequestChange.as_view(), name='workshoprequest_edit'),
        url(r'^assign/$', views.workshoprequest_assign, name='workshoprequest_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', views.workshoprequest_assign, name='workshoprequest_assign'),
    ])),

    # deprecated: old swc/dc workshop requests
    url(r'^requests/$', deprecated_views.AllEventRequests.as_view(), name='all_eventrequests'),
    url(r'^request/(?P<request_id>\d+)/', include([
        url(r'^$', deprecated_views.EventRequestDetails.as_view(), name='eventrequest_details'),
        url(r'^set_state/(?P<state>[\w]+)/$', deprecated_views.EventRequestSetState.as_view(), name='eventrequest_set_state'),
        url(r'^accept_event/$', deprecated_views.eventrequest_accept_event, name='eventrequest_accept_event'),
        url(r'^edit/$', deprecated_views.EventRequestChange.as_view(), name='eventrequest_edit'),
        url(r'^assign/$', deprecated_views.eventrequest_assign, name='eventrequest_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', deprecated_views.eventrequest_assign, name='eventrequest_assign'),
    ])),

    # deprecated: dc self-organized workshop requests
    url(r'^dc_selforganized_requests/$', deprecated_views.AllDCSelfOrganizedEventRequests.as_view(), name='all_dcselforganizedeventrequests'),
    url(r'^dc_selforganized_request/(?P<request_id>\d+)/', include([
        url(r'^$', deprecated_views.DCSelfOrganizedEventRequestDetails.as_view(), name='dcselforganizedeventrequest_details'),
        url(r'^set_state/(?P<state>[\w\.-]+)/$', deprecated_views.DCSelfOrganizedEventRequestSetState.as_view(), name='dcselforganizedeventrequest_set_state'),
        url(r'^accept_event/$', deprecated_views.dcselforganizedeventrequest_accept_event, name='dcselforganizedeventrequest_accept_event'),
        url(r'^edit/$', deprecated_views.DCSelfOrganizedEventRequestChange.as_view(), name='dcselforganizedeventrequest_edit'),
        url(r'^assign/$', deprecated_views.dcselforganizedeventrequest_assign, name='dcselforganizedeventrequest_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', deprecated_views.dcselforganizedeventrequest_assign, name='dcselforganizedeventrequest_assign'),
    ])),

    # deprecated: workshop submissions
    url(r'^submissions/$', deprecated_views.AllEventSubmissions.as_view(), name='all_eventsubmissions'),
    url(r'^submission/(?P<submission_id>\d+)/', include([
        url(r'^$', deprecated_views.EventSubmissionDetails.as_view(), name='eventsubmission_details'),
        url(r'^set_state/(?P<state>[\w\.-]+)/$', deprecated_views.EventSubmissionSetState.as_view(), name='eventsubmission_set_state'),
        url(r'^accept_event/$', deprecated_views.eventsubmission_accept_event, name='eventsubmission_accept_event'),
        url(r'^edit/$', deprecated_views.EventSubmissionChange.as_view(), name='eventsubmission_edit'),
        url(r'^assign/$', deprecated_views.eventsubmission_assign, name='eventsubmission_assign'),
        url(r'^assign/(?P<person_id>[\w\.-]+)/$', deprecated_views.eventsubmission_assign, name='eventsubmission_assign'),
    ])),

    # deprecated: profile update requests
    url(r'^profile_updates/$', deprecated_views.AllProfileUpdateRequests.as_view(), name='all_profileupdaterequests'),
    url(r'^profile_updates/closed/$', deprecated_views.AllClosedProfileUpdateRequests.as_view(), name='all_closed_profileupdaterequests'),
    url(r'^profile_update/(?P<request_id>\d+)/', include([
        url(r'^$', deprecated_views.profileupdaterequest_details, name='profileupdaterequest_details'),
        url(r'^fix/$', deprecated_views.ProfileUpdateRequestFix.as_view(), name='profileupdaterequest_fix'),
        url(r'^discard/$', deprecated_views.profileupdaterequest_discard, name='profileupdaterequest_discard'),
        url(r'^accept/$', deprecated_views.profileupdaterequest_accept, name='profileupdaterequest_accept'),
        url(r'^accept/(?P<person_id>[\w\.-]+)/$', deprecated_views.profileupdaterequest_accept, name='profileupdaterequest_accept'),
    ])),

    # deprecated: invoices
    url(r'^invoices/$', deprecated_views.AllInvoiceRequests.as_view(), name='all_invoicerequests'),
    url(r'^invoice/(?P<request_id>\d+)/', include([
        url(r'^$', deprecated_views.InvoiceRequestDetails.as_view(), name='invoicerequest_details'),
        url(r'^edit/$', deprecated_views.InvoiceRequestUpdate.as_view(), name='invoicerequest_edit'),
    ])),
]
