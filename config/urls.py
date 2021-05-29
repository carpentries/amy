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
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.contenttypes.views import shortcut
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django_comments.views.comments import post_comment, comment_done
from markdownx.views import ImageUploadView, MarkdownifyView
from workshops.views import logout_then_login_with_msg
from workshops.util import login_required

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dispatch')),
    path(settings.ADMIN_URL, admin.site.urls),  # {% url 'admin:index' %}

    path('autoemails/', include('autoemails.urls')),
    path('api/v1/', include('api.urls')),  # REST API v1
    path('dashboard/', include('dashboard.urls')),
    path('requests/', include('extrequests.urls')),
    path('forms/', include('extforms.urls')),  # external, anonymous user-accessible forms
    path('fiscal/', include('fiscal.urls')),
    path('reports/', include('reports.urls')),
    path('trainings/', include('trainings.urls')),
    path('workshops/', include('workshops.urls')),
    path('select_lookups/', include('workshops.lookups')),  # autocomplete lookups
    path('terms/', include('consents.urls')),

    # for webhooks from Mailgun
    path('mail_hooks/', include('anymail.urls')),

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

    # for commenting system
    path('comments/', include([
        path('post/', login_required(post_comment), name='comments-post-comment'),
        path('posted/', login_required(comment_done), name='comments-comment-done'),
        path('cr/<int:content_type_id>/<int:object_id>/', login_required(shortcut), name='comments-url-redirect'),
    ])),

    # for markdown upload & preview
    path('markdownx/', include([
        path('markdownify/', login_required(MarkdownifyView.as_view()), name='markdownx_markdownify'),
        path('upload/', login_required(ImageUploadView.as_view()), name='markdownx_upload'),
    ])),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

redirect_urlpatterns = [
    path('workshops/', RedirectView.as_view(pattern_name='dispatch')),
    path('workshops/admin-dashboard/', RedirectView.as_view(pattern_name='admin-dashboard')),
    path('workshops/trainee-dashboard/', RedirectView.as_view(pattern_name='trainee-dashboard')),
    path('workshops/trainee-dashboard/training_progress/', RedirectView.as_view(pattern_name='training-progress')),
    path('workshops/autoupdate_profile/', RedirectView.as_view(pattern_name='autoupdate_profile')),

    path('workshops/training_requests/', RedirectView.as_view(pattern_name='all_trainingrequests')),
    path('workshops/training_requests/merge', RedirectView.as_view(pattern_name='trainingrequests_merge')),
    path('workshops/bulk_upload_training_request_scores', RedirectView.as_view(pattern_name='bulk_upload_training_request_scores')),
    path('workshops/bulk_upload_training_request_scores/confirm', RedirectView.as_view(pattern_name='bulk_upload_training_request_scores_confirmation')),

    path('workshops/workshop_requests/', RedirectView.as_view(pattern_name='all_workshoprequests')),

    path('workshops/organizations/', RedirectView.as_view(pattern_name='all_organizations')),
    path('workshops/memberships/', RedirectView.as_view(pattern_name='all_memberships')),

    path('workshops/reports/membership_trainings_stats/', RedirectView.as_view(pattern_name='membership_trainings_stats')),
    path('workshops/reports/workshop_issues/', RedirectView.as_view(pattern_name='workshop_issues')),
    path('workshops/reports/instructor_issues/', RedirectView.as_view(pattern_name='instructor_issues')),
    path('workshops/reports/duplicate_persons/', RedirectView.as_view(pattern_name='duplicate_persons')),
    path('workshops/reports/duplicate_training_requests/', RedirectView.as_view(pattern_name='duplicate_training_requests')),

    path('workshops/trainings/', RedirectView.as_view(pattern_name='all_trainings')),
    path('workshops/trainees/', RedirectView.as_view(pattern_name='all_trainees')),
    path('workshops/request_training/', RedirectView.as_view(pattern_name='training_request', permanent=True)),
]

urlpatterns += redirect_urlpatterns

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
