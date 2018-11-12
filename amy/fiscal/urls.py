from django.urls import path, include

from fiscal import views

urlpatterns = [
    # organizations
    path('organizations/', include([
        path('', views.AllOrganizations.as_view(), name='all_organizations'),
        path('add/', views.OrganizationCreate.as_view(), name='organization_add'),
    ])),
    path('organization/<str:org_domain>/', include([
        path('', views.OrganizationDetails.as_view(), name='organization_details'),
        path('edit/', views.OrganizationUpdate.as_view(), name='organization_edit'),
        path('delete/', views.OrganizationDelete.as_view(), name='organization_delete'),
    ])),

    # memberships
    path('memberships/', include([
        path('', views.AllMemberships.as_view(), name='all_memberships'),
        path('add/', views.MembershipCreate.as_view(), name='membership_add'),
    ])),
    path('membership/<int:membership_id>/', include([
        path('', views.MembershipDetails.as_view(), name='membership_details'),
        path('edit/', views.MembershipUpdate.as_view(), name='membership_edit'),
        path('delete/', views.MembershipDelete.as_view(), name='membership_delete'),
    ])),

    # sponsorships
    path('sponsorships/add/', views.SponsorshipCreate.as_view(), name='sponsorship_add'),
    path('sponsorship/<int:pk>/delete/', views.SponsorshipDelete.as_view(), name='sponsorship_delete'),
]
