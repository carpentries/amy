from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from workshops.models import Role

from ..templatetags.content_types import get_content_type_objects_by_ids


class TestGetContentTypeObjectsByIds(TestCase):
    def test_get_content_type_objects_by_ids(self):
        # Arrange
        # some sample model used here (Role)
        ct = ContentType.objects.get_for_model(Role)
        role1 = Role.objects.create(name="Test Inactivation 1")
        role2 = Role.objects.create(name="Test Inactivation 2")

        # Act
        objects = get_content_type_objects_by_ids(ct, [role1.pk, role2.pk])

        # Assert
        self.assertEqual(list(objects), [role1, role2])
