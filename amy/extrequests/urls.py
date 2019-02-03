from django.urls import path, include

from extrequests import views, deprecated_views


urlpatterns = [
    # training requests
    path('training_requests/', views.all_trainingrequests, name='all_trainingrequests'),
    path('training_requests/merge', views.trainingrequests_merge, name='trainingrequests_merge'),
    path('training_request/<int:pk>/', include([
        path('', views.trainingrequest_details, name='trainingrequest_details'),
        path('edit/', views.TrainingRequestUpdate.as_view(), name='trainingrequest_edit'),
    ])),
    path('bulk_upload_training_request_scores/', views.bulk_upload_training_request_scores, name='bulk_upload_training_request_scores'),
    path('bulk_upload_training_request_scores/confirm/', views.bulk_upload_training_request_scores_confirmation, name='bulk_upload_training_request_scores_confirmation'),

    # unified workshop requests
    path('workshop_requests/', views.AllWorkshopRequests.as_view(), name='all_workshoprequests'),
    path('workshop_request/<int:request_id>/', include([
        path('', views.WorkshopRequestDetails.as_view(), name='workshoprequest_details'),
        path('set_state/<slug:state>/', views.WorkshopRequestSetState.as_view(), name='workshoprequest_set_state'),
        path('accept_event/', views.workshoprequest_accept_event, name='workshoprequest_accept_event'),
        path('edit/', views.WorkshopRequestChange.as_view(), name='workshoprequest_edit'),
        path('assign/', views.WorkshopRequestAssign.as_view(), name='workshoprequest_assign'),
        path('assign/<int:person_id>/', views.WorkshopRequestAssign.as_view(), name='workshoprequest_assign'),
    ])),

    # deprecated: old swc/dc workshop requests
    path('eventrequests/', deprecated_views.AllEventRequests.as_view(), name='all_eventrequests'),
    path('eventrequest/<int:request_id>/', include([
        path('', deprecated_views.EventRequestDetails.as_view(), name='eventrequest_details'),
        path('set_state/<slug:state>/', deprecated_views.EventRequestSetState.as_view(), name='eventrequest_set_state'),
        path('accept_event/', deprecated_views.eventrequest_accept_event, name='eventrequest_accept_event'),
        path('edit/', deprecated_views.EventRequestChange.as_view(), name='eventrequest_edit'),
        path('assign/', deprecated_views.EventRequestAssign.as_view(), name='eventrequest_assign'),
        path('assign/<int:person_id>/', deprecated_views.EventRequestAssign.as_view(), name='eventrequest_assign'),
    ])),

    # deprecated: dc self-organized workshop requests
    path('dc_selforganized_requests/', deprecated_views.AllDCSelfOrganizedEventRequests.as_view(), name='all_dcselforganizedeventrequests'),
    path('dc_selforganized_request/<int:request_id>/', include([
        path('', deprecated_views.DCSelfOrganizedEventRequestDetails.as_view(), name='dcselforganizedeventrequest_details'),
        path('set_state/<slug:state>/', deprecated_views.DCSelfOrganizedEventRequestSetState.as_view(), name='dcselforganizedeventrequest_set_state'),
        path('accept_event/', deprecated_views.dcselforganizedeventrequest_accept_event, name='dcselforganizedeventrequest_accept_event'),
        path('edit/', deprecated_views.DCSelfOrganizedEventRequestChange.as_view(), name='dcselforganizedeventrequest_edit'),
        path('assign/', deprecated_views.DCSelfOrganizedEventRequestAssign.as_view(), name='dcselforganizedeventrequest_assign'),
        path('assign/<int:person_id>/', deprecated_views.DCSelfOrganizedEventRequestAssign.as_view(), name='dcselforganizedeventrequest_assign'),
    ])),

    # deprecated: workshop submissions
    path('submissions/', deprecated_views.AllEventSubmissions.as_view(), name='all_eventsubmissions'),
    path('submission/<int:submission_id>/', include([
        path('', deprecated_views.EventSubmissionDetails.as_view(), name='eventsubmission_details'),
        path('set_state/<slug:state>/', deprecated_views.EventSubmissionSetState.as_view(), name='eventsubmission_set_state'),
        path('accept_event/', deprecated_views.eventsubmission_accept_event, name='eventsubmission_accept_event'),
        path('edit/', deprecated_views.EventSubmissionChange.as_view(), name='eventsubmission_edit'),
        path('assign/', deprecated_views.EventSubmissionAssign.as_view(), name='eventsubmission_assign'),
        path('assign/<int:person_id>/', deprecated_views.EventSubmissionAssign.as_view(), name='eventsubmission_assign'),
    ])),
]
