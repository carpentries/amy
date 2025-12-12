from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase

from recruitment.filters import InstructorRecruitmentFilter
from recruitment.models import InstructorRecruitment
from workshops.models import Event, Organization, Person


class TestInstructorRecruitmentFilter(TestCase):
    def test_filters(self) -> None:
        # Arrange
        filter_set = InstructorRecruitmentFilter()
        # Act
        keys = filter_set.filters.keys()
        # Assert
        self.assertEqual(
            keys,
            {
                "assigned_to",
                "status",
                "online_inperson",
                "country",
                "curricula",
                "order_by",
            },
        )

    def test_status_filter_choices(self) -> None:
        # Arrange
        filter_set = InstructorRecruitmentFilter()

        # Act
        choices = filter_set.filters["status"].extra["choices"]

        # Assert
        self.assertEqual(choices, list(InstructorRecruitment.STATUS_CHOICES))

    def test_assigned_to_filter_choices_empty(self) -> None:
        # Arrange
        filter_set = InstructorRecruitmentFilter()

        # Act
        choices = filter_set.filters["assigned_to"].extra["queryset"]

        # Assert
        self.assertEqual(list(choices), [])

    def test_assigned_to_filter_choices(self) -> None:
        # Arrange
        event = Event.objects.create(slug="test-event", host=Organization.objects.all()[0])
        person = Person.objects.create(username="test_user")
        InstructorRecruitment.objects.create(event=event, assigned_to=person)

        filter_set = InstructorRecruitmentFilter()

        # Act
        choices = filter_set.filters["assigned_to"].extra["queryset"]

        # Assert
        self.assertEqual(list(choices), [person])

    def test_invalid_values_for_online_inperson(self) -> None:
        # Arrange
        test_data = [
            "test",
            "online/inperson",
            " online",
        ]
        filterset = InstructorRecruitmentFilter({})
        field = filterset.filters["online_inperson"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert
                with self.assertRaises(ValidationError):
                    field.validate(value)

    def test_valid_values_for_online_inperson(self) -> None:
        # Arrange
        test_data = [
            "",
            None,
            "online",
            "inperson",
        ]
        filterset = InstructorRecruitmentFilter({})
        field = filterset.filters["online_inperson"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert no exception
                field.validate(value)

    def test_invalid_values_for_order_by(self) -> None:
        # Arrange
        test_data = [
            "event_start",  # single _ instead of double __
            "-event__end",
            "proximity",
            " event__start",  # space
            "calculated_priority",  # unavailable
        ]
        filterset = InstructorRecruitmentFilter({})
        field = filterset.filters["order_by"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert
                with self.assertRaises(ValidationError):
                    field.validate(value)

    def test_valid_values_for_order_by(self) -> None:
        # Arrange
        test_data = [
            "",
            None,
            "event__start",
            "-event__start",
            "-calculated_priority",
        ]
        filterset = InstructorRecruitmentFilter({})
        field = filterset.filters["order_by"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert no exception
                field.validate(value)

    def test_filter_online_inperson__online(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = InstructorRecruitmentFilter({})
        name = "status"
        # Act
        filterset.filter_online_inperson(qs_mock, name, "online")
        # Assert
        qs_mock.filter.assert_called_once_with(event__tags__name="online")
        qs_mock.exclude.assert_not_called()

    def test_filter_online_inperson__inperson(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = InstructorRecruitmentFilter({})
        name = "status"
        # Act
        filterset.filter_online_inperson(qs_mock, name, "inperson")
        # Assert
        qs_mock.filter.assert_not_called()
        qs_mock.exclude.assert_called_once_with(event__tags__name="online")

    def test_filter_online_inperson__other_value(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = InstructorRecruitmentFilter({})
        name = "status"
        # Act
        result = filterset.filter_online_inperson(qs_mock, name, "other")
        # Assert
        qs_mock.filter.assert_not_called()
        qs_mock.exclude.assert_not_called()
        self.assertEqual(result, qs_mock)
