from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls.base import reverse

from communityroles.models import (
    CommunityRole,
    CommunityRoleConfig,
    CommunityRoleInactivation,
)
from workshops.models import Badge, Person


class TestCommunityRoleConfigModel(TestCase):
    def test_str(self):
        # Arrange
        instance = CommunityRoleConfig(
            name="test",
            display_name="Test Role",
            link_to_award=True,
            award_badge_limit=Badge.objects.first(),
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=ContentType.objects.get_for_model(Badge),
        )
        # Act
        representation = str(instance)
        # Assert
        self.assertEqual(representation, "Test Role")


class TestCommunityRoleInactivationModel(TestCase):
    def test_str(self):
        # Arrange
        instance = CommunityRoleInactivation(
            name="test inactivation",
        )
        # Act
        representation = str(instance)
        # Assert
        self.assertEqual(representation, "test inactivation")


class TestCommunityRoleModel(TestCase):
    def setUp(self):
        self.config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test Role",
            link_to_award=True,
            link_to_membership=True,
            additional_url=True,
        )
        self.person = Person.objects.create(
            personal="Test",
            family="Family",
            email="test.person@example.org",
        )
        self.community_role = CommunityRole(
            config=self.config,
            person=self.person,
        )

    def test_str(self):
        # Act
        representation = str(self.community_role)
        # Assert
        self.assertEqual(
            representation,
            'Community Role "Test Role" for Test Family <test.person@example.org>',
        )

    def test_get_absolute_url(self):
        # Arrange
        self.community_role.save()
        # Act
        url = self.community_role.get_absolute_url()
        # Assert
        self.assertEqual(
            url, reverse("communityrole_details", args=[self.community_role.pk])
        )
