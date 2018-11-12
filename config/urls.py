"""amy URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from workshops.views import logout_then_login_with_msg

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dispatch')),
    path('admin/', admin.site.urls),
]

if settings.ENABLE_PYDATA:
    PyData_urlpatterns = [
        path('workshops/', include('pydata.urls')),
    ]
    urlpatterns += PyData_urlpatterns

urlpatterns += [
    path('api/v1/', include('api.urls')),  # REST API v1
    path('dashboard/', include('dashboard.urls')),
    path('requests/', include('extrequests.urls')),
    path('forms/', include('extforms.urls')),  # external, anonymous user-accessible forms
    path('fiscal/', include('fiscal.urls')),
    path('reports/', include('reports.urls')),
    path('trainings/', include('trainings.urls')),
    path('workshops/', include('workshops.urls')),
    path('select_lookups/', include('workshops.lookups')),  # autocomplete lookups

    # django views for authentication
    path('account/login/',
         auth_views.LoginView.as_view(
             template_name="account/login.html",
             extra_context={"title": "Log in"},
         ),
         name='login'),

    path('account/logout/',
         logout_then_login_with_msg,
         name='logout'),

    path('account/password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name="account/password_reset.html",
         ),
         name='password_reset'),

    path('account/password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name="account/password_reset_done.html",
         ),
         name='password_reset_done'),

    re_path(r'^account/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
            r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
            auth_views.PasswordResetConfirmView.as_view(
                template_name="account/password_reset_confirm.html",
            ),
            name='password_reset_confirm'),

    path('account/reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name="account/password_reset_complete.html",
         ),
         name='password_reset_complete'),

    # Login with GitHub credentials
    path('', include('social_django.urls', namespace='social')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
