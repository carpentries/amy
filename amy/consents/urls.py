from django.urls import include, path

from consents import views

urlpatterns = [
    path('action_required/', views.action_required_terms, name='action_required_terms'),
    path('<int:person_id>/', include([
        path('consents/add/', views.ConsentsUpdate.as_view(), name='consents_add'),
    ])),
]
