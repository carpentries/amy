from django.conf.urls import url, include

from extforms import views

urlpatterns = [
    url(r'^swc/request/$', views.SWCEventRequest.as_view(), name='swc_workshop_request'),
    url(r'^swc/request/confirm/$', views.SWCEventRequestConfirm.as_view(), name='swc_workshop_request_confirm'),
    url(r'^dc/request/$', views.DCEventRequest.as_view(), name='dc_workshop_request'),
    url(r'^dc/request/confirm/$', views.DCEventRequestConfirm.as_view(), name='dc_workshop_request_confirm'),
    url(r'^dc/request_selforganized/$', views.DCSelfOrganizedEventRequest.as_view(), name='dc_workshop_selforganized_request'),
    url(r'^dc/request_selforganized/confirm/$', views.DCSelfOrganizedEventRequestConfirm.as_view(), name='dc_workshop_selforganized_request_confirm'),
    url(r'^submit/$', views.EventSubmission.as_view(), name='event_submit'),
    # url(r'^submit/confirm/$', views.EventSubmissionConfirm.as_view(), name='event_submission_confirm'),
    url(r'^update_profile/$', views.profileupdaterequest_create, name='profileupdate_request'),
    url(r'^request_training/$', views.trainingrequest_create, name='training_request'),
]
