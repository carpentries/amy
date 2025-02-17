from django.db.utils import IntegrityError
from django.test import TestCase

from communityroles.models import CommunityRole, CommunityRoleConfig
from recruitment.forms import (
    InstructorRecruitmentAddSignupForm,
    InstructorRecruitmentChangeStateForm,
    InstructorRecruitmentCreateForm,
    InstructorRecruitmentSignupChangeStateForm,
    InstructorRecruitmentSignupUpdateForm,
)
from workshops.models import Person


class TestInstructorRecruitmentCreateForm(TestCase):
    def test_empty_payload(self) -> None:
        # Arrange
        data = {}
        # Act
        form = InstructorRecruitmentCreateForm(data)
        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors.keys(), set())

    def test_clean_success(self) -> None:
        # Arrange
        data = {"notes": "Lorem ipsum", "priority": 2}
        # Act
        form = InstructorRecruitmentCreateForm(data)
        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors.keys(), set())

    def test_save_fails(self) -> None:
        """Form needs to be used in a view to properly save object."""
        # Arrange
        data = {"notes": "Lorem ipsum"}
        form = InstructorRecruitmentCreateForm(data)
        # Act & Assert
        with self.assertRaises(IntegrityError):
            form.save()


class TestInstructorRecruitmentAddSignupForm(TestCase):
    def _prepare_person(self) -> Person:
        person = Person.objects.create(personal="Test", family="User", username="test_user")
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        CommunityRole.objects.create(
            config=config,
            person=person,
        )
        return person

    def test_empty_payload(self) -> None:
        # Arrange
        data = {}
        # Act
        form = InstructorRecruitmentAddSignupForm(data)
        # Assert
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.keys(), {"person"})

    def test_clean_success(self) -> None:
        # Arrange
        person = self._prepare_person()
        data = {"person": person.pk}
        # Act
        form = InstructorRecruitmentAddSignupForm(data)
        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors.keys(), set())

    def test_save_fails(self) -> None:
        """Form needs to be used in a view to properly save object."""
        # Arrange
        person = self._prepare_person()
        data = {"person": person.pk, "notes": "Lorem ipsum"}
        form = InstructorRecruitmentAddSignupForm(data)
        # Act & Assert
        with self.assertRaises(IntegrityError):
            form.save()


class TestInstructorRecruitmentSignupChangeStateForm(TestCase):
    def test_empty_payload(self) -> None:
        # Arrange
        data = {}
        # Act
        form = InstructorRecruitmentSignupChangeStateForm(data)
        # Assert
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.keys(), {"action"})

    def test_clean_success(self) -> None:
        # Arrange
        data = {"action": "confirm"}
        # Act
        form = InstructorRecruitmentSignupChangeStateForm(data)
        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors.keys(), set())


class TestInstructorRecruitmentChangeStateForm(TestCase):
    def test_empty_payload(self) -> None:
        # Arrange
        data = {}
        # Act
        form = InstructorRecruitmentChangeStateForm(data)
        # Assert
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.keys(), {"action"})

    def test_clean_success(self) -> None:
        # Arrange
        data = {"action": "close"}
        # Act
        form = InstructorRecruitmentChangeStateForm(data)
        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors.keys(), set())


class TestInstructorRecruitmentSignupUpdateForm(TestCase):
    def test_empty_payload(self) -> None:
        # Arrange
        data = {}
        # Act
        form = InstructorRecruitmentSignupUpdateForm(data)
        # Assert
        self.assertTrue(form.is_valid())

    def test_clean_success(self) -> None:
        # Arrange
        data = {"notes": "test"}
        # Act
        form = InstructorRecruitmentSignupUpdateForm(data)
        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors.keys(), set())
