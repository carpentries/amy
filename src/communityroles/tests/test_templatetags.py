from datetime import date

from django.test import TestCase

from src.communityroles.models import CommunityRole, CommunityRoleConfig
from src.communityroles.templatetags.communityroles import (
    community_role_human_dates,
    get_community_role,
)
from src.workshops.models import Person


class TestCommunityRolesTemplateTag(TestCase):
    def test_get_community_role(self) -> None:
        # Arrange
        person = Person.objects.create(personal="Test", family="User", email="test@user.com")
        role_name = "instructor"
        config = CommunityRoleConfig.objects.create(
            name=role_name,
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        role_orig = CommunityRole.objects.create(config=config, person=person)
        # Act
        role_found = get_community_role(person, role_name)
        # Assert
        self.assertEqual(role_orig, role_found)

    def test_get_community_role__config_not_found(self) -> None:
        # Arrange
        person = Person.objects.create(personal="Test", family="User", email="test@user.com")
        role_name = "instructor"
        config = CommunityRoleConfig.objects.create(
            name=role_name,
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        CommunityRole.objects.create(config=config, person=person)
        # Act
        role_found = get_community_role(person, "fake_role")
        # Assert
        self.assertEqual(role_found, None)

    def test_get_community_role__person_not_found(self) -> None:
        # Arrange
        person = Person.objects.create(personal="Test", family="User", email="test@user.com")
        fake_person = Person.objects.create(
            personal="Fake",
            family="Person",
            email="fake@person.com",
            username="fake_user",
        )
        role_name = "instructor"
        config = CommunityRoleConfig.objects.create(
            name=role_name,
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        CommunityRole.objects.create(config=config, person=person)
        # Act
        role_found = get_community_role(fake_person, role_name)
        # Assert
        self.assertEqual(role_found, None)


class TestCommunityRoleHumanDatesTemplateTag(TestCase):
    def test_community_role_human_dates(self) -> None:
        # Arrange
        self.instructor_community_role_config = CommunityRoleConfig.objects.create(
            name="instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        person = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        community_role = CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person,
            start=date(2022, 9, 17),
            end=None,
        )

        # Act
        date_display = community_role_human_dates(community_role)

        # Assert
        self.assertEqual(date_display, "Sep 17, 2022 - present")
