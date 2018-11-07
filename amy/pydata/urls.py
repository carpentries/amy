from django.conf.urls import url, include

from pydata import views


urlpatterns = [
    url(r'^events/import/?$',
        views.ConferenceImport.as_view(),
        name='event_import'),
    url(r'^persons/import/?$',
        views.PersonImport.as_view(),
        name='person_import'),
    url(r'^tasks/import/?$',
        views.TaskImport.as_view(),
        name='task_import'),
    url(r'^sponsorships/import/?$',
        views.SponsorshipImport.as_view(),
        name='sponsorship_import'),

    url(r'^bulk-import/', include([
        url(r'^$',
            views.BulkImportEventSelect.as_view(),
            name='bulk_import_select'),
        url(r'^(?P<slug>[\w-]+)/person/?$',
            views.PersonBulkImport.as_view(),
            name='bulk_import_person'),
        url(r'^(?P<slug>[\w-]+)/task/?$',
            views.TaskBulkImport.as_view(),
            name='bulk_import_task'),
        url(r'^(?P<slug>[\w-]+)/sponsorship/?$',
            views.SponsorshipBulkImport.as_view(),
            name='bulk_import_sponsorship'),
    ])),
]
