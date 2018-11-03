from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path('', views.dispatch, name='dispatch'),

    # admin dashboard main page
    path('admin/', views.admin_dashboard, name='admin-dashboard'),

    # trainee dashboard and trainee-available views
    path('trainee/', views.trainee_dashboard, name='trainee-dashboard'),
    path('trainee/training_progress/', views.training_progress, name='training-progress'),
    path('trainee/autoupdate_profile/', views.autoupdate_profile, name='autoupdate_profile'),
]
