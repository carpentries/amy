from unittest.mock import MagicMock

from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.views import View

from src.api.v1.permissions import DjangoModelPermissionsWithView
from src.recruitment.models import InstructorRecruitment
from src.workshops.models import Person


class TestDjangoModelPermissionsWithView(TestCase):
    def setUp(self) -> None:
        self.model = InstructorRecruitment
        meta = self.model._meta
        self.permissions = {
            "add": Permission.objects.get_by_natural_key(
                codename=f"add_{meta.model_name}",
                app_label=meta.app_label,
                model=str(meta.model_name),
            ),
            "change": Permission.objects.get_by_natural_key(
                codename=f"change_{meta.model_name}",
                app_label=meta.app_label,
                model=str(meta.model_name),
            ),
            "delete": Permission.objects.get_by_natural_key(
                codename=f"delete_{meta.model_name}",
                app_label=meta.app_label,
                model=str(meta.model_name),
            ),
            "view": Permission.objects.get_by_natural_key(
                codename=f"view_{meta.model_name}",
                app_label=meta.app_label,
                model=str(meta.model_name),
            ),
        }

    def test_has_permission_GET__no_view_perm(self) -> None:
        """Ensure GET request won't pass when user doesn't have `view` permission."""
        # Arrange
        permission_class = DjangoModelPermissionsWithView()
        user = Person(personal="Test", family="User", email="test@example.org")
        request = RequestFactory().get("/")
        request.user = user
        permission_class._queryset = MagicMock()  # type: ignore[method-assign]
        permission_class._queryset.return_value.model = self.model
        view = View()
        # Act
        result = permission_class.has_permission(request, view)  # type: ignore[arg-type]
        # Assert
        self.assertEqual(result, False)

    def test_has_permission_GET__other_perms(self) -> None:
        """Ensure GET request won't pass when user has other permissions than `view`
        permission from the same model."""
        # Arrange
        permission_class = DjangoModelPermissionsWithView()
        user = Person.objects.create(
            personal="Test",
            family="User",
            email="test@example.org",
            is_active=True,  # needed for applying the permissions
        )
        user.user_permissions.add(
            self.permissions["add"],
            self.permissions["change"],
            self.permissions["delete"],
        )
        request = RequestFactory().get("/")
        request.user = user
        permission_class._queryset = MagicMock()  # type: ignore[method-assign]
        permission_class._queryset.return_value.model = self.model
        view = View()
        # Act
        result = permission_class.has_permission(request, view)  # type: ignore[arg-type]
        # Assert
        self.assertEqual(result, False)

    def test_has_permission_GET__view_perm(self) -> None:
        """Ensure GET request passes when user has `view` permission."""
        # Arrange
        permission_class = DjangoModelPermissionsWithView()
        user = Person.objects.create(
            personal="Test",
            family="User",
            email="test@example.org",
            is_active=True,  # needed for applying the permissions
        )
        user.user_permissions.add(self.permissions["view"])
        request = RequestFactory().get("/")
        request.user = user
        permission_class._queryset = MagicMock()  # type: ignore[method-assign]
        permission_class._queryset.return_value.model = self.model
        view = View()
        # Act
        result = permission_class.has_permission(request, view)  # type: ignore[arg-type]
        # Assert
        self.assertEqual(result, True)
