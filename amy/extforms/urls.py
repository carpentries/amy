from django.urls import path

from extforms import views

urlpatterns = [
    # these views create a some sort of workshop-request -
    # a request for SWC, or for DC workshop, or a request for self-organized DC
    # workshop
    path('request_training/', views.TrainingRequestCreate.as_view(), name='training_request'),
    path('request_training/confirm/', views.TrainingRequestConfirm.as_view(), name='training_request_confirm'),
    path('workshop/', views.WorkshopLanding.as_view(), name='workshop_landing'),
    path('request_workshop/', views.WorkshopRequestCreate.as_view(), name='workshop_request'),
    path('request_workshop/confirm/', views.WorkshopRequestConfirm.as_view(), name='workshop_request_confirm'),
    path('inquiry/', views.WorkshopInquiryRequestCreate.as_view(), name='workshop_inquiry'),
    path('inquiry/confirm/', views.WorkshopInquiryRequestConfirm.as_view(), name='workshop_inquiry_confirm'),
    path('self-organized/', views.SelfOrganizedSubmissionCreate.as_view(), name='selforganized_submission'),
    path('self-organized/confirm/', views.SelfOrganizedSubmissionConfirm.as_view(), name='selforganized_submission_confirm'),
    # forms below have been turned off:
    path('swc/request/', views.SWCEventRequest.as_view(), name='swc_workshop_request'),
    path('dc/request/', views.DCEventRequest.as_view(), name='dc_workshop_request'),
    path('submit/', views.EventSubmission.as_view(), name='event_submit'),
    path('dc/request_selforganized/', views.DCSelfOrganizedEventRequest.as_view(), name='dc_workshop_selforganized_request'),
    path('update_profile/', views.ProfileUpdateRequestView.as_view(), name='profileupdate_request'),
]
