from consents import views
from django.urls import include, path

urlpatterns = [
    path('',
        views.action_required_terms, name='action_required_terms'),
    path('<int:person_id>/consents/', include([
        path('add', views.ConsentsUpdate.as_view(), name='consents_add'),
    ])),
]
