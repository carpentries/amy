import unittest

from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.urls import reverse
from django.views.generic import RedirectView, View
from markdownx.views import ImageUploadView, MarkdownifyView
from rest_framework.views import APIView

from config import urls
from workshops.models import Person
from workshops.tests.base import TestBase
from workshops.utils.access import (
    LoginNotRequiredMixin,
    OnlyForAdminsMixin,
    admin_required,
    login_not_required,
    login_required,
)


def get_resolved_urls(url_patterns):
    """Copy-pasted from
    http://stackoverflow.com/questions/1275486/django-how-can-i-see-a-list-of-urlpatterns
    """  # noqa: line too long
    url_patterns_resolved = []
    for entry in url_patterns:
        if hasattr(entry, "url_patterns"):
            url_patterns_resolved += get_resolved_urls(entry.url_patterns)
        else:
            url_patterns_resolved.append(entry)
    return url_patterns_resolved


def get_view_by_name(name):
    views = get_resolved_urls(urls.urlpatterns)
    try:
        return next(v.callback for v in views if v.name == name)
    except StopIteration:
        raise ValueError("No view named {}".format(name))


class TestViews(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpGroups()

        amy_admins = Group.objects.get(name="amy_administrators")
        view_all = Group.objects.get(name="view_all")
        membership_admins = Group.objects.get(name="membership_administrators")
        workshop_admins = Group.objects.get(name="workshop_administrators")

        # superuser who doesn't belong to Admin group should have access to
        # admin dashboard
        self.admin = Person.objects.create_superuser(
            username="superuser",
            personal="Super",
            family="User",
            email="superuser@example.org",
            password="superuser",
        )
        self.person_consent_required_terms(self.admin)
        assert view_all not in self.admin.groups.all()

        # user belonging to Admin group should have access to admin dashboard
        self.amy_admin = Person.objects.create_user(
            username="admin",
            personal="Bob",
            family="Admin",
            email="admin@example.org",
            password="admin",
        )
        self.person_consent_required_terms(self.amy_admin)
        self.amy_admin.groups.add(view_all)
        self.amy_admin.groups.add(amy_admins)

        # executive council members should have access to admin dashboard too
        self.council = Person.objects.create_user(
            username="council",
            personal="Bob",
            family="Council",
            email="council@example.org",
            password="council",
        )
        self.person_consent_required_terms(self.council)
        self.council.groups.add(view_all)

        # membership team should have access to admin dashboard too
        self.membership_admin = Person.objects.create_user(
            username="membership",
            personal="Bob",
            family="Membership",
            email="membership@example.org",
            password="membership",
        )
        self.person_consent_required_terms(self.membership_admin)
        self.membership_admin.groups.add(view_all)
        self.membership_admin.groups.add(membership_admins)

        # workshop admins should have access to admin dashboard too
        self.workshop_admin = Person.objects.create_user(
            username="workshop",
            personal="Bob",
            family="Workshop",
            email="workshop@example.org",
            password="workshop",
        )
        self.person_consent_required_terms(self.workshop_admin)
        self.workshop_admin.groups.add(view_all)
        self.workshop_admin.groups.add(workshop_admins)

        # user with access only to trainee/instructor dashboard
        self.trainee = Person.objects.create_user(
            username="trainee",
            personal="Bob",
            family="Trainee",
            email="trainee@example.org",
            password="trainee",
        )
        self.person_consent_required_terms(self.trainee)
        assert amy_admins not in self.trainee.groups.all()
        assert view_all not in self.trainee.groups.all()

    def assert_accessible(self, url, user=None):
        if user is not None:
            self.client.login(username=user, password=user)
        response = self.client.get(url)
        self.client.logout()

        self.assertEqual(response.status_code, 200)

    def assert_inaccessible(self, url, user=None):
        if user is not None:
            self.client.login(username=user, password=user)
        response = self.client.get(url)
        self.client.logout()

        # We should get 403 page (forbidden) or be redirected to login page.
        if response.status_code != 403:
            login_url = "{}?next={}".format(reverse("login"), url)
            self.assertRedirects(response, login_url)

    def test_function_based_view_restricted_to_admins(self):
        """
        Test that a view decorated with @admin_required is accessible only
        for Admins.
        """
        view_name = "admin-dashboard"
        view = get_view_by_name(view_name)
        assert view._access_control_list == [admin_required]
        url = reverse(view_name)

        self.assert_accessible(url, user="superuser")
        self.assert_accessible(url, user="admin")
        self.assert_accessible(url, user="council")
        self.assert_accessible(url, user="membership")
        self.assert_accessible(url, user="workshop")
        self.assert_inaccessible(url, user="trainee")
        self.assert_inaccessible(url, user=None)

    def test_function_based_view_restricted_to_authorized_users(self):
        """
        Test that a view decorated with @login_required is accessible
        only for Admins and Trainees.
        """
        view_name = "instructor-dashboard"
        view = get_view_by_name(view_name)
        assert view._access_control_list == [login_required]
        url = reverse(view_name)

        self.assert_accessible(url, user="superuser")
        self.assert_accessible(url, user="admin")
        self.assert_accessible(url, user="council")
        self.assert_accessible(url, user="membership")
        self.assert_accessible(url, user="workshop")
        self.assert_accessible(url, user="trainee")
        self.assert_inaccessible(url, user=None)

    @unittest.skip("No view uses @login_not_required decorator")
    def test_function_based_view_accessible_to_unauthorized_users(self):
        """
        Test that a view decorated with @login_not_required is accessible to
        everyone.
        """
        view_name = "profileupdate_request"
        view = get_view_by_name(view_name)
        assert view._access_control_list == [login_not_required]
        url = reverse(view_name)

        self.assert_accessible(url, user="superuser")
        self.assert_accessible(url, user="admin")
        self.assert_accessible(url, user="council")
        self.assert_accessible(url, user="membership")
        self.assert_accessible(url, user="workshop")
        self.assert_accessible(url, user="trainee")
        self.assert_accessible(url, user=None)

    def test_class_based_view_restricted_to_admins(self):
        """
        Test that a view with OnlyForAdminsMixin is accessible only for Admins.
        """
        view_name = "all_workshoprequests"
        view = get_view_by_name(view_name)
        assert OnlyForAdminsMixin in view.view_class.__mro__
        url = reverse(view_name)

        self.assert_accessible(url, user="superuser")
        self.assert_accessible(url, user="admin")
        self.assert_accessible(url, user="council")
        self.assert_accessible(url, user="membership")
        self.assert_accessible(url, user="workshop")
        self.assert_inaccessible(url, user="trainee")
        self.assert_inaccessible(url, user=None)

    def test_class_based_view_accessible_to_unauthorized_users(self):
        """
        Test that a view with LoginNotRequiredMixin is accessible to everyone.
        """
        view_name = "workshop_request"
        view = get_view_by_name(view_name)
        assert LoginNotRequiredMixin in view.view_class.__mro__
        url = reverse(view_name)

        self.assert_accessible(url, user="superuser")
        self.assert_accessible(url, user="admin")
        self.assert_accessible(url, user="council")
        self.assert_accessible(url, user="membership")
        self.assert_accessible(url, user="workshop")
        self.assert_accessible(url, user="trainee")
        self.assert_accessible(url, user=None)

    # def test_membership_view(self):
    #     """
    #     Test that memberships can be viewed by all admins,
    #     but only created by membership admins.
    #     """
    #     view_name = "membership_details"
    #     view = get_view_by_name(view_name)
    #     assert view._access_control_list == [login_required]
    #     url = reverse(view_name)

    #     self.assert_accessible(url, user="superuser")
    #     self.assert_accessible(url, user="admin")
    #     self.assert_accessible(url, user="council")
    #     self.assert_accessible(url, user="membership")
    #     self.assert_accessible(url, user="workshop")
    #     self.assert_accessible(url, user="trainee")
    #     self.assert_inaccessible(url, user=None)

    IGNORED_VIEWS = [
        # auth
        "login",
        "logout",
        "password_reset",
        "password_reset_done",
        "password_reset_confirm",
        "password_reset_complete",
        # 'password_change',
        # 'password_change_done',
        # python-social-auth
        "begin",
        "complete",
        "disconnect",
        "disconnect_individual",
        # anymail
        "amazon_ses_inbound_webhook",
        "mailgun_inbound_webhook",
        "mailjet_inbound_webhook",
        "postmark_inbound_webhook",
        "sendgrid_inbound_webhook",
        "sparkpost_inbound_webhook",
        "amazon_ses_tracking_webhook",
        "mailgun_tracking_webhook",
        "mailjet_tracking_webhook",
        "postmark_tracking_webhook",
        "sendgrid_tracking_webhook",
        "sendinblue_tracking_webhook",
        "sparkpost_tracking_webhook",
        "mandrill_webhook",
        "mandrill_tracking_webhook",
    ]

    def test_all_views_have_explicit_access_control_defined(self):
        """
        Test that all views have explicitly defined access control:

        - In the case of function based views, test if the view is decorated
          with an access control decorator like @login_not_required.

        - In the case of class based views, test if the view has access control
          mixin like LoginNotRequiredMixin.

        Ignores:

        - views listed on IGNORED_VIEWS,

        - Django-admin views,

        - Rest API views.

        """

        all_urls = get_resolved_urls(urls.urlpatterns)

        # ignore views listed on IGNORED_VIEWS list
        all_urls = [
            u
            for u in all_urls
            if not hasattr(u, "name") or u.name not in self.IGNORED_VIEWS
        ]

        for url in all_urls:
            with self.subTest(view=url):
                acl = getattr(url.callback, "_access_control_list", None)
                model_admin = getattr(url.callback, "model_admin", None)
                admin_site = getattr(url.callback, "admin_site", None)

                # v.callback is always a function, even when the view is
                # class based. We try to find the class implementing the view.
                view_class = getattr(url.callback, "view_class", None)
                cls = getattr(url.callback, "cls", None)
                class_ = view_class or cls or None

                is_function_based_view = (
                    model_admin is None and admin_site is None and class_ is None
                )

                if is_function_based_view:
                    self.assertTrue(
                        acl is not None,
                        "You have a function based view with no access control"
                        " decorator. This view is probably accessible to every"
                        " user. If this is what you want, use "
                        "@login_not_required decorator. Questionable view: "
                        '"{}"'.format(url),
                    )
                    self.assertEqual(
                        len(acl),
                        1,
                        "You have more than one access control "
                        "decorator defined in this view.",
                    )

                else:  # class based view
                    is_markdownx_view = class_ is not None and (
                        issubclass(class_, MarkdownifyView)
                        or issubclass(class_, ImageUploadView)
                    )

                    if is_markdownx_view:
                        self.assertTrue(
                            acl is not None,
                            "Markdownx views must be decorated "
                            "with `login_required`.",
                        )
                    else:
                        self.assertTrue(
                            acl is None,
                            "It looks like you used access control decorator "
                            "on a class based view. Use mixin instead.",
                        )

                        is_model_admin = isinstance(model_admin, ModelAdmin)
                        is_admin_site = isinstance(admin_site, AdminSite)
                        is_api_view = class_ is not None and issubclass(class_, APIView)
                        is_redirect_view = class_ is not None and issubclass(
                            class_, RedirectView
                        )
                        is_view = class_ is not None and issubclass(class_, View)

                        if is_model_admin or is_admin_site:
                            pass  # ignore admin views
                        elif is_api_view:
                            pass  # ignore REST API views
                        elif is_redirect_view:
                            pass  # ignore pure redirect views
                        else:
                            assert is_view

                            mixins = set(class_.__mro__)
                            desired_mixins = {
                                OnlyForAdminsMixin,
                                LoginNotRequiredMixin,
                                LoginRequiredMixin,
                            }
                            found = mixins & desired_mixins

                            self.assertNotEqual(
                                len(found),
                                0,
                                "The view {} ({}) lacks access control mixin "
                                "and is probably accessible to every user. If "
                                "this is what you want, use "
                                "LoginNotRequiredMixin.".format(class_.__name__, url),
                            )
                            self.assertEqual(
                                len(found),
                                1,
                                "You have more than one access control mixin "
                                "defined in this view.",
                            )
