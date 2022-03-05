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
        self.assertEqual(keys, {"assigned_to", "status"})

    def test_status_filter_choices(self) -> None:
        # Arrange
        filter_set = InstructorRecruitmentFilter()

        # Act
        choices = filter_set.filters["status"].extra["choices"]

        # Assert
        self.assertEqual(choices, InstructorRecruitment.STATUS_CHOICES)

    def test_assigned_to_filter_choices_empty(self) -> None:
        # Arrange
        filter_set = InstructorRecruitmentFilter()

        # Act
        choices = filter_set.filters["assigned_to"].extra["queryset"]

        # Assert
        self.assertEqual(list(choices), [])

    def test_assigned_to_filter_choices(self) -> None:
        # Arrange
        event = Event.objects.create(
            slug="test-event", host=Organization.objects.first()
        )
        person = Person.objects.create(username="test_user")
        InstructorRecruitment.objects.create(event=event, assigned_to=person)

        filter_set = InstructorRecruitmentFilter()

        # Act
        choices = filter_set.filters["assigned_to"].extra["queryset"]

        # Assert
        self.assertEqual(list(choices), [person])
