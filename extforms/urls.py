from django.conf.urls import url, include

from extforms import views

urlpatterns = [
    # these views create a some sort of workshop-request -
    # a request for SWC, or for DC workshop, or a request for self-organized DC
    # workshop
    url(r'^swc/request/$', views.SWCEventRequest.as_view(), name='swc_workshop_request'),
    url(r'^swc/request/confirm/$', views.SWCEventRequestConfirm.as_view(), name='swc_workshop_request_confirm'),
    url(r'^dc/request/$', views.DCEventRequest.as_view(), name='dc_workshop_request'),
    url(r'^dc/request/confirm/$', views.DCEventRequestConfirm.as_view(), name='dc_workshop_request_confirm'),
    url(r'^dc/request_selforganized/$', views.DCSelfOrganizedEventRequest.as_view(), name='dc_workshop_selforganized_request'),
    url(r'^dc/request_selforganized/confirm/$', views.DCSelfOrganizedEventRequestConfirm.as_view(), name='dc_workshop_selforganized_request_confirm'),
    # an existing SWC workshop submission has been turned off
    url(r'^submit/$', views.EventSubmission.as_view(), name='event_submit'),
    # disabled as per @maneesha's request
    # url(r'^submit/confirm/$', views.EventSubmissionConfirm.as_view(), name='event_submission_confirm'),
    url(r'^update_profile/$', views.ProfileUpdateRequestView.as_view(), name='profileupdate_request'),
    url(r'^update_profile/confirm/$', views.ProfileUpdateRequestConfirm.as_view(), name='profileupdate_request_confirm'),
    url(r'^request_training/$', views.TrainingRequestCreate.as_view(), name='training_request'),
    url(r'^request_training/confirm/$', views.TrainingRequestConfirm.as_view(), name='training_request_confirm'),
]
