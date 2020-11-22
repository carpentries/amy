from django.urls import path, include

from extrequests import views


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
        path('accept_event/', views.WorkshopRequestAcceptEvent.as_view(), name='workshoprequest_accept_event'),
        path('edit/', views.WorkshopRequestChange.as_view(), name='workshoprequest_edit'),
        path('assign/', views.WorkshopRequestAssign.as_view(), name='workshoprequest_assign'),
        path('assign/<int:person_id>/', views.WorkshopRequestAssign.as_view(), name='workshoprequest_assign'),
    ])),

    # workshop inquiries
    path('workshop_inquiries/', views.AllWorkshopInquiries.as_view(), name='all_workshopinquiries'),
    path('workshop_inquiry/<int:inquiry_id>/', include([
        path('', views.WorkshopInquiryDetails.as_view(), name='workshopinquiry_details'),
        path('set_state/<slug:state>/', views.WorkshopInquirySetState.as_view(), name='workshopinquiry_set_state'),
        path('accept_event/', views.WorkshopInquiryAcceptEvent.as_view(), name='workshopinquiry_accept_event'),
        path('edit/', views.WorkshopInquiryChange.as_view(), name='workshopinquiry_edit'),
        path('assign/', views.WorkshopInquiryAssign.as_view(), name='workshopinquiry_assign'),
        path('assign/<int:person_id>/', views.WorkshopInquiryAssign.as_view(), name='workshopinquiry_assign'),
    ])),

    # self-organized submissions
    path('selforganised_submissions/', views.AllSelfOrganisedSubmissions.as_view(), name='all_selforganisedsubmissions'),
    path('selforganised_submission/<int:submission_id>/', include([
        path('', views.SelfOrganisedSubmissionDetails.as_view(), name='selforganisedsubmission_details'),
        path('set_state/<slug:state>/', views.SelfOrganisedSubmissionSetState.as_view(), name='selforganisedsubmission_set_state'),
        path('accept_event/', views.SelfOrganisedSubmissionAcceptEvent.as_view(), name='selforganisedsubmission_accept_event'),
        path('edit/', views.SelfOrganisedSubmissionChange.as_view(), name='selforganisedsubmission_edit'),
        path('assign/', views.SelfOrganisedSubmissionAssign.as_view(), name='selforganisedsubmission_assign'),
        path('assign/<int:person_id>/', views.SelfOrganisedSubmissionAssign.as_view(), name='selforganisedsubmission_assign'),
    ])),
]
