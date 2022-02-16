from datetime import date, timedelta
from typing import Optional

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

    def test_is_active(self):
        # Arrange
        person = Person(personal="Test", family="User", email="test@user.com")
        config = CommunityRoleConfig(
            name="test_config",
            display_name="Test Config",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        inactivation = CommunityRoleInactivation(name="test inactivation")
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        data: list[
            tuple[
                Optional[CommunityRoleInactivation],  # role.inactivation
                Optional[date],  # role.start
                Optional[date],  # role.end
                bool,  # expected result
            ]
        ] = [
            # cases when we have inactivation set: always False
            (inactivation, None, None, False),
            (inactivation, yesterday, tomorrow, False),
            (inactivation, yesterday, None, False),
            (inactivation, None, tomorrow, False),
            # cases when no start/no end
            (None, None, None, True),
            # cases when both start and end are available
            (None, yesterday, tomorrow, True),
            (None, tomorrow, yesterday, False),
            (None, today, tomorrow, True),
            (None, yesterday, today, False),
            # cases when only start is provided
            (None, tomorrow, None, False),
            (None, today, None, True),
            (None, yesterday, None, True),
            # cases when only end is provided
            (None, None, tomorrow, True),
            (None, None, today, False),
            (None, None, yesterday, False),
        ]
        for inactivation, start, end, expected in data:
            with self.subTest(inactivation=inactivation, start=start, end=end):
                community_role = CommunityRole(
                    config=config,
                    person=person,
                    inactivation=inactivation,
                    start=start,
                    end=end,
                )

                # Act
                result = community_role.is_active()

                # Assert
                self.assertEqual(result, expected)
