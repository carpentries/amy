from datetime import date
from unittest.mock import patch

from django.test import TestCase

from recruitment.models import InstructorRecruitment, RecruitmentPriority
from workshops.models import Event, Organization, Tag


class TestInstructorRecruitment(TestCase):
    @patch("recruitment.models.date")
    def test_calculate_priority__not_online(self, mock_date):
        # Arrange
        mock_date.today.return_value = date(2022, 1, 1)  # force today's date
        dates = [
            (date(2021, 12, 31), RecruitmentPriority.HIGH),  # past
            (date(2022, 1, 1), RecruitmentPriority.HIGH),  # same date
            (date(2022, 2, 1), RecruitmentPriority.HIGH),
            (date(2022, 3, 2), RecruitmentPriority.HIGH),  # border dates
            (date(2022, 3, 3), RecruitmentPriority.MEDIUM),  # border dates
            (date(2022, 3, 10), RecruitmentPriority.MEDIUM),
            (date(2022, 3, 31), RecruitmentPriority.MEDIUM),  # border dates
            (date(2022, 4, 1), RecruitmentPriority.LOW),  # border dates
            (date(2023, 12, 31), RecruitmentPriority.LOW),  # way in future
        ]

        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )

        for start_date, expected_priority in dates:
            event.start = start_date
            event.save()

            # Act
            priority = InstructorRecruitment.calculate_priority(event)
            # Assert
            self.assertEqual(priority, expected_priority, start_date)

    @patch("recruitment.models.date")
    def test_calculate_priority__online(self, mock_date):
        # Arrange
        mock_date.today.return_value = date(2022, 1, 1)  # force today's date
        dates = [
            (date(2021, 12, 31), RecruitmentPriority.HIGH),  # past
            (date(2022, 1, 1), RecruitmentPriority.HIGH),  # same date
            (date(2022, 1, 30), RecruitmentPriority.HIGH),
            (date(2022, 1, 31), RecruitmentPriority.HIGH),  # border dates
            (date(2022, 2, 1), RecruitmentPriority.MEDIUM),  # border dates
            (date(2022, 2, 28), RecruitmentPriority.MEDIUM),
            (date(2022, 3, 1), RecruitmentPriority.MEDIUM),  # border dates
            (date(2022, 3, 2), RecruitmentPriority.LOW),  # border dates
            (date(2023, 12, 31), RecruitmentPriority.LOW),  # way in future
        ]

        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        event.tags.add(Tag.objects.get(name="online"))

        for start_date, expected_priority in dates:
            event.start = start_date
            event.save()

            # Act
            priority = InstructorRecruitment.calculate_priority(event)
            # Assert
            self.assertEqual(priority, expected_priority, start_date)
