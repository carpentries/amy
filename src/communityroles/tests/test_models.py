from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls.base import reverse

from src.communityroles.models import (
    CommunityRole,
    CommunityRoleConfig,
    CommunityRoleInactivation,
)
from src.workshops.models import Award, Badge, Person


class TestCommunityRoleConfigModel(TestCase):
    def test_str(self) -> None:
        # Arrange
        instance = CommunityRoleConfig(
            name="test",
            display_name="Test Role",
            link_to_award=True,
            award_badge_limit=Badge.objects.all()[0],
            link_to_membership=True,
            link_to_partnership=False,
            additional_url=True,
            generic_relation_content_type=ContentType.objects.get_for_model(Badge),
        )
        # Act
        representation = str(instance)
        # Assert
        self.assertEqual(representation, "Test Role")


class TestCommunityRoleInactivationModel(TestCase):
    def test_str(self) -> None:
        # Arrange
        instance = CommunityRoleInactivation(
            name="test inactivation",
        )
        # Act
        representation = str(instance)
        # Assert
        self.assertEqual(representation, "test inactivation")


class TestCommunityRoleQuery(TestCase):
    def test_active(self) -> None:
        # Arrange
        today = date.today()
        self.instructor_badge = Badge.objects.create(name="instructor", title="Instructor")
        self.instructor_community_role_config = CommunityRoleConfig.objects.create(
            name="instructor",
            link_to_award=True,
            award_badge_limit=self.instructor_badge,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        award1 = Award.objects.create(person=person1, badge=self.instructor_badge, awarded=date(2022, 1, 1))
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person1,
            award=award1,
            start=today + timedelta(days=30),
            end=None,
        )
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        award2 = Award.objects.create(person=person2, badge=self.instructor_badge)
        crole2 = CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person2,
            award=award2,
            start=today - timedelta(days=7),
            end=today + timedelta(days=7),
        )
        person3 = Person.objects.create(username="test3", personal="Test3", family="User", email="test3@example.org")
        award3 = Award.objects.create(person=person3, badge=self.instructor_badge)
        crole3 = CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person3,
            award=award3,
            start=None,
            end=today + timedelta(days=30),
        )
        person4 = Person.objects.create(username="test4", personal="Test4", family="User", email="test4@example.org")
        award4 = Award.objects.create(person=person4, badge=self.instructor_badge)
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person4,
            award=award4,
            start=None,
            end=today - timedelta(days=30),
        )
        person5 = Person.objects.create(username="test5", personal="Test5", family="User", email="test5@example.org")
        award5 = Award.objects.create(person=person5, badge=self.instructor_badge)
        crole5 = CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person5,
            award=award5,
            start=None,
            end=None,
        )
        person6 = Person.objects.create(username="test6", personal="Test6", family="User", email="test6@example.org")
        award6 = Award.objects.create(person=person6, badge=self.instructor_badge)
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person6,
            award=award6,
            start=None,
            end=None,
            inactivation=CommunityRoleInactivation.objects.create(name="Inactive"),
        )

        # Act
        active_roles = CommunityRole.objects.active()

        # Assert
        self.assertEqual(set(active_roles), {crole2, crole3, crole5})


class TestCommunityRoleModel(TestCase):
    def setUp(self) -> None:
        self.config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test Role",
            link_to_award=True,
            link_to_membership=True,
            link_to_partnership=False,
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

    def test_str(self) -> None:
        # Act
        representation = str(self.community_role)
        # Assert
        self.assertEqual(
            representation,
            'Community Role "Test Role" for Test Family <test.person@example.org>',
        )

    def test_get_absolute_url(self) -> None:
        # Arrange
        self.community_role.save()
        # Act
        url = self.community_role.get_absolute_url()
        # Assert
        self.assertEqual(url, reverse("communityrole_details", args=[self.community_role.pk]))

    def test_is_active(self) -> None:
        # Arrange
        person = Person(personal="Test", family="User", email="test@user.com")
        config = CommunityRoleConfig(
            name="test_config",
            display_name="Test Config",
            link_to_award=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        inactivation = CommunityRoleInactivation(name="test inactivation")
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        data: list[
            tuple[
                CommunityRoleInactivation | None,  # role.inactivation
                date | None,  # role.start
                date | None,  # role.end
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
        for inactivation_, start, end, expected in data:
            with self.subTest(inactivation=inactivation_, start=start, end=end):
                community_role = CommunityRole(
                    config=config,
                    person=person,
                    inactivation=inactivation_,
                    start=start,
                    end=end,
                )

                # Act
                result = community_role.is_active()

                # Assert
                self.assertEqual(result, expected)
