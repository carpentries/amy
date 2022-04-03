from django.db.utils import IntegrityError
from django.test import TestCase

from recruitment.forms import (
    InstructorRecruitmentCreateForm,
    InstructorRecruitmentSignupChangeStateForm,
)


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
        data = {"notes": "Lorem ipsum"}
        # Act
        form = InstructorRecruitmentCreateForm(data)
        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors.keys(), set())

    def test_save_fails(self) -> None:
        # Arrange
        data = {"notes": "Lorem ipsum"}
        form = InstructorRecruitmentCreateForm(data)
        # Act & Assert
        with self.assertRaises(IntegrityError):
            form.save()  # form needs to be used in a view to properly save object


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
