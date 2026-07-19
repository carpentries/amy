from django.urls import include, path

from src.consents import views

urlpatterns = [
    path("action_required/", views.ActionRequiredTerms.as_view(), name="action_required_terms"),
    path(
        "<int:person_id>/",
        include(
            [
                path("consents/add/", views.ConsentsUpdate.as_view(), name="consents_add"),
            ]
        ),
    ),
]
