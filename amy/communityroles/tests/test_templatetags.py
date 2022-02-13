from django.test import TestCase

from communityroles.models import CommunityRole, CommunityRoleConfig
from communityroles.templatetags.communityroles import get_community_role
from workshops.models import Person


class TestCommunityRolesTemplateTags(TestCase):
    def test_get_community_role(self):
        # Arrange
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
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

    def test_get_community_role__config_not_found(self):
        # Arrange
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
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
        role_found = get_community_role(person, "fake_role")
        # Assert
        self.assertEqual(role_found, None)

    def test_get_community_role__person_not_found(self):
        # Arrange
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
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
