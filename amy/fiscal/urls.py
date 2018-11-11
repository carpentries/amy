from django.conf.urls import url, include

from fiscal import views

urlpatterns = [
    # organizations
    url(r'^organizations/', include([
        url(r'^$', views.AllOrganizations.as_view(), name='all_organizations'),
        url(r'^add/$', views.OrganizationCreate.as_view(), name='organization_add'),
    ])),
    url(r'^organization/(?P<org_domain>[\w\.-]+)/', include([
        url(r'^$', views.OrganizationDetails.as_view(), name='organization_details'),
        url(r'^edit/$', views.OrganizationUpdate.as_view(), name='organization_edit'),
        url(r'^delete/$', views.OrganizationDelete.as_view(), name='organization_delete'),
    ])),

    # memberships
    url(r'^memberships/', include([
        url(r'^$', views.AllMemberships.as_view(), name='all_memberships'),
        url(r'^add/$', views.MembershipCreate.as_view(), name='membership_add'),
    ])),
    url(r'^membership/(?P<membership_id>\d+)/', include([
        url(r'^$', views.MembershipDetails.as_view(), name='membership_details'),
        url(r'^edit/$', views.MembershipUpdate.as_view(), name='membership_edit'),
        url(r'^delete/$', views.MembershipDelete.as_view(), name='membership_delete'),
    ])),

    # sponsorships
    url(r'^sponsorships/add/$', views.SponsorshipCreate.as_view(), name='sponsorship_add'),
    url(r'^sponsorship/(?P<pk>\d+)/delete/$', views.SponsorshipDelete.as_view(), name='sponsorship_delete'),
]
