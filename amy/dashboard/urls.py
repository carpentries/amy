from django.urls import include, path

from dashboard import views

urlpatterns = [
    path('', views.dispatch, name='dispatch'),

    # admin dashboard main page
    path('admin/', include([
        path('', views.admin_dashboard, name='admin-dashboard'),
        path('search/', views.search, name='search'),
    ])),

    # trainee dashboard and trainee-available views
    path('trainee/', include([
        path('', views.trainee_dashboard, name='trainee-dashboard'),
        path('training_progress/', views.training_progress, name='training-progress'),
        path('autoupdate_profile/', views.autoupdate_profile, name='autoupdate_profile'),
    ])),
]
