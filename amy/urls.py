from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

urlpatterns = [
    url(r'^workshops/admin/', include(admin.site.urls)),
    url(r'^workshops/', include('workshops.urls')),
    # url(r'^account/', include('django.contrib.auth.urls')),

    # django views for authentication
    # taken in almost exact form from django.contrib.auth.views.urls:
    url(r'^account/login/$', auth_views.login,
        {"template_name": "account/login.html",
         "extra_context": {"title": "Log in"}}, name='login'),
    url(r'^account/logout/$', auth_views.logout,
        {"template_name": "account/logged_out.html"}, name='logout'),
    url(r'^account/password_reset/$',
        auth_views.password_reset,
        {"template_name": "account/password_reset.html"},
        name='password_reset'),
    url(r'^account/password_reset/done/$',
        auth_views.password_reset_done,
        {"template_name": "account/password_reset_done.html"},
        name='password_reset_done'),
    url(r'^account/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        {"template_name": "account/password_reset_confirm.html"},
        name='password_reset_confirm'),
    url(r'^account/reset/done/$',
        auth_views.password_reset_complete,
        {"template_name": "account/password_reset_complete.html"},
        name='password_reset_complete'),

    # TODO: implement URLs below (add templates, etc.)
    # url(r'^account/password_change/$', 'django.contrib.auth.views.password_change', name='password_change'),
    # url(r'^account/password_change/done/$', 'django.contrib.auth.views.password_change_done', name='password_change_done'),

    url(r'^selectable/', include('selectable.urls')),

    # REST API v1
    url(r'^api/v1/', include('api.urls')),
]
