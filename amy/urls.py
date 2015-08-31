from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^workshops/admin/', include(admin.site.urls)),
    url(r'^workshops/', include('workshops.urls')),
    # url(r'^account/', include('django.contrib.auth.urls')),

    # django views for authentication
    # taken in almost exact form from django.contrib.auth.views.urls:
    url(r'^account/login/$', 'django.contrib.auth.views.login',
        {"template_name": "account/login.html",
         "extra_context": {"title": "Log in"}}, name='login'),
    url(r'^account/logout/$', 'django.contrib.auth.views.logout',
        {"template_name": "account/logged_out.html"}, name='logout'),

    # TODO: implement URLs below (add templates, etc.)
    # url(r'^account/password_change/$', 'django.contrib.auth.views.password_change', name='password_change'),
    # url(r'^account/password_change/done/$', 'django.contrib.auth.views.password_change_done', name='password_change_done'),
    # url(r'^account/password_reset/$', 'django.contrib.auth.views.password_reset', name='password_reset'),
    # url(r'^account/password_reset/done/$', 'django.contrib.auth.views.password_reset_done', name='password_reset_done'),
    # url(r'^account/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
    #     'django.contrib.auth.views.password_reset_confirm',
    #     name='password_reset_confirm'),
    # url(r'^account/reset/done/$', 'django.contrib.auth.views.password_reset_complete', name='password_reset_complete'),

    url(r'^selectable/', include('selectable.urls')),

    # REST API v1
    url(r'^api/v1/', include('api.urls', namespace='api')),
)
