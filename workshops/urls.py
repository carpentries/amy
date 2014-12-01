from django.conf.urls import url

from workshops import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^sites/?$', views.all_sites, name='all_sites'),
    url(r'^site/(?P<site_domain>[\w\.]+)/?$', views.site_details, name='site_details'),
]
