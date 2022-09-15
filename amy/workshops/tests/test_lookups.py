from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q
from django.http.response import Http404
from django.test import RequestFactory
from django.urls import reverse

from workshops.lookups import AwardLookupView, GenericObjectLookupView, urlpatterns
from workshops.models import Award, Badge, Lesson, Person
from workshops.tests.base import (
    TestBase,
    TestViewPermissionsMixin,
    consent_to_all_required_consents,
)


class TestLookups(TestBase):
    """Test suite for Django-Autocomplete-Light lookups."""

    def setUp(self):
        # prepare urlpatterns; only include lookup views that are restricted
        # to logged-in users and/or admins
        self.patterns_nonrestricted = ("language-lookup",)
        self.urlpatterns = filter(
            lambda pattern: pattern.name not in self.patterns_nonrestricted, urlpatterns
        )

    def test_login_regression(self):
        """Make sure lookups are login-protected"""
        for pattern in self.urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 403, pattern.name)  # forbidden

        self._setUpUsersAndLogin()
        for pattern in self.urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 200, pattern.name)  # OK


class TestAwardLookupView(TestBase):
    def setUpView(self, term: str = "", badge: Optional[int] = None) -> AwardLookupView:
        # path doesn't matter
        request = RequestFactory().get("/" if badge is None else f"/?badge={badge}")
        view = AwardLookupView(request=request, term=term)
        return view

    def test_get_queryset_no_term(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(set(queryset), set(Award.objects.all()))

    def test_get_queryset_simple_term(self):
        # Arrange
        term = "term"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(
            set(queryset),
            set(
                Award.objects.filter(
                    Q(person__personal__icontains=term)
                    | Q(person__middle__icontains=term)
                    | Q(person__family__icontains=term)
                    | Q(person__email__icontains=term)
                    | Q(badge__name__icontains=term)
                )
            ),
        )

    def test_get_queryset_badge(self):
        # Arrange
        badge = self.swc_instructor.pk
        view = self.setUpView(badge=badge)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(set(queryset), set(Award.objects.filter(badge__pk=badge)))

    def test_get_queryset_badge_and_term(self):
        # Arrange
        badge = self.swc_instructor.pk
        term = "term"
        view = self.setUpView(term=term, badge=badge)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(
            set(queryset),
            set(
                Award.objects.filter(badge__pk=badge).filter(
                    Q(person__personal__icontains=term)
                    | Q(person__middle__icontains=term)
                    | Q(person__family__icontains=term)
                    | Q(person__email__icontains=term)
                    | Q(badge__name__icontains=term)
                )
            ),
        )


class TestGenericObjectLookupView(TestBase):
    def setUpRequest(self, path: str) -> WSGIRequest:
        return RequestFactory().get(path)

    def setUpView(
        self, content_type: Optional[ContentType] = None
    ) -> GenericObjectLookupView:
        # path doesn't matter
        path = "/"
        if content_type:
            path = f"/?content_type={content_type.pk}"
        request = self.setUpRequest(path)
        view = GenericObjectLookupView(request=request, content_type=content_type)
        return view

    def test_get_queryset_no_content_type_returns_empty_results(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertTrue(queryset.model is None)
        # QuerySets created without model param don't support comparisons to
        # EmptyQuerySet or checking if underlying `query` is empty. So the easiest way
        # I figured was to check if `.model` is None.

    def test_get_queryset_invalid_content_type_raises_404(self):
        # Arrange
        view = self.setUpView(
            content_type=ContentType(pk=1000000, app_label="Test", model="Test")
        )
        # Act & Assert
        with self.assertRaises(Http404):
            view.get_queryset()

    def test_get_queryset_concrete_content_type_returns_queryset_for_that_model(self):
        # Arrange
        content_type = ContentType.objects.get_for_model(Lesson)
        view = self.setUpView(content_type=content_type)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(queryset.model, Lesson)
        self.assertEqual(set(queryset), set(Lesson.objects.all()))

    def test_get_response(self):
        # Arrange
        content_type = ContentType.objects.get_for_model(Badge)
        view = self.setUpView(content_type=content_type)
        request = self.setUpRequest("/")

        # Act
        result = view.get(request)
        # Assert
        self.assertEqual(
            result.content.decode("utf-8"),
            '{"results": ['
            '{"text": "Software Carpentry Instructor", "id": 1}, '
            '{"text": "Data Carpentry Instructor", "id": 2}, '
            '{"text": "Maintainer", "id": 3}, '
            '{"text": "Trainer", "id": 4}, '
            '{"text": "Mentor", "id": 5}, '
            '{"text": "Mentee", "id": 6}, '
            '{"text": "Library Carpentry Instructor", "id": 7}, '
            '{"text": "Instructor", "id": '
            f"{self.instructor_badge.pk}"
            "}]}",
        )

    def test_permissions_no_content_type(self):
        # Arrange
        content_type = ""
        view = self.setUpView()
        # Act
        result = view.test_func(content_type)
        # Assert
        self.assertFalse(result)

    def test_permissions_content_type_doesnt_exist(self):
        # Arrange
        content_type = "-1"
        view = self.setUpView()
        # Act
        result = view.test_func(content_type)
        # Assert
        self.assertFalse(result)


class TestGenericObjectLookupViewUserPermissions(TestViewPermissionsMixin, TestBase):
    """Integration tests for user passing test on specific Model instances.

    If user has "view_model" permissions, they should be let in."""

    def setUp(self):
        super().setUp()
        self.user = Person.objects.create_user(
            "testuser",
            "Personal",
            "Family",
            "personal.family@example.org",
            "secretpassword",
        )
        self.model = Badge
        self.permissions = ["view_badge"]
        self.methods = ["GET"]
        self.content_type = ContentType.objects.get_for_model(self.model)
        self.view_url = (
            reverse("generic-object-lookup") + f"?content_type={self.content_type.pk}"
        )
        # prevent redirect to accept terms from middleware
        consent_to_all_required_consents(self.user)
