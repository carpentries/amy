from django.urls import path, include
from  consents import views 


urlpatterns = [
    path('',
        views.action_required_terms, name='action_required_terms'),
    path('<int:consent_id>/', include([
        path('', views.ConsentDetails.as_view(), name='consent_details'),
        path('add/', views.ConsentCreate.as_view(), name='consent_add'),
        path('delete/', views.ConsentDelete.as_view(), name='consent_delete'),
    ])),
]
