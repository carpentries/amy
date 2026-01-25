from typing import Any

from django.test import TestCase

from src.communityroles.models import (
    CommunityRole,
    CommunityRoleConfig,
    CommunityRoleInactivation,
)
from src.workshops.forms import TaskForm
from src.workshops.models import Event, Organization, Person, Role


class TestTaskForm(TestCase):
    def setUp(self) -> None:
        instructor_training_organization = Organization.objects.create(
            domain="carpentries.org",
            fullname="Instructor Training",
        )
        swc = Organization.objects.create(
            domain="software-carpentry.org",
            fullname="Software Carpentry",
        )
        host = Organization.objects.all()[0]
        self.event1 = Event.objects.create(
            slug="test-event2",
            host=host,
            administrator=swc,
        )
        self.event2 = Event.objects.create(
            slug="test-event1",
            host=host,
            administrator=instructor_training_organization,
        )
        self.person = Person.objects.create(personal="Test", family="User", email="test@example.org")
        role = Role.objects.create(name="instructor", verbose_name="Instructor")
        self.payload: dict[str, Any] = {
            "event": None,
            "person": self.person.pk,
            "role": role.pk,
        }
        self.instructor_community_role_config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        self.trainer_community_role_config = CommunityRoleConfig.objects.create(
            name="trainer",
            display_name="Trainer",
            link_to_award=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        self.inactivation = CommunityRoleInactivation.objects.create(name="Test")

    def test_clean__no_community_roles__instructor(self) -> None:
        # Arrange
        self.payload["event"] = self.event1
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertTrue(result)

    def test_clean__no_community_roles__trainer(self) -> None:
        # Arrange
        self.payload["event"] = self.event2
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertTrue(result)

    def test_clean__inactive_community_role__instructor(self) -> None:
        # Arrange
        self.payload["event"] = self.event1
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=self.person,
            inactivation=self.inactivation,
        )
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertFalse(result)
        self.assertEqual(form.errors.keys(), {"role"})

    def test_clean__inactive_community_role__trainer(self) -> None:
        # Arrange
        self.payload["event"] = self.event2
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=self.person,
            inactivation=self.inactivation,
        )
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertFalse(result)
        self.assertEqual(form.errors.keys(), {"role"})

    def test_clean__active_community_roles__instructor(self) -> None:
        # Arrange
        self.payload["event"] = self.event1
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=self.person,
        )
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertTrue(result)

    def test_clean__active_community_roles__trainer(self) -> None:
        # Arrange
        self.payload["event"] = self.event2
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=self.person,
        )
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertTrue(result)

    def test_clean__mixed_active_inactive_community_roles__instructor(self) -> None:
        # Arrange
        self.payload["event"] = self.event1
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=self.person,
        )
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=self.person,
            inactivation=self.inactivation,
        )
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertTrue(result)

    def test_clean__mixed_active_inactive_community_roles__trainer(self) -> None:
        # Arrange
        self.payload["event"] = self.event2
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=self.person,
        )
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=self.person,
            inactivation=self.inactivation,
        )
        form = TaskForm(self.payload)
        # Act
        result = form.is_valid()
        # Assert
        self.assertTrue(result)
