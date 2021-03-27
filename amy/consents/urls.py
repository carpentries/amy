from consents import views
from django.urls import include, path

urlpatterns = [
    path('<int:person_id>/consents/', include([
        path('add', views.ConsentsUpdate.as_view(), name='consents_add'),
    ])),
]
