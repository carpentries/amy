from django.urls import path

from . import views

app_name = "autoemails"

urlpatterns = [
    path("email_response/<int:pk>/", views.generic_schedule_email, name="email_response"),
]
