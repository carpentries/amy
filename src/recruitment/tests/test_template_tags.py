from datetime import date

from django.test import TestCase

from src.recruitment.models import (
    InstructorRecruitment,
    InstructorRecruitmentSignup,
    RecruitmentPriority,
)
from src.recruitment.templatetags.instructorrecruitment import (
    get_event_conflicts,
    get_events_nearby,
    get_signup_conflicts,
    priority_label,
)
from src.workshops.models import Event


class TestInstructorRecruitmentTemplateTags(TestCase):
    def test_get_event_conflicts(self) -> None:
        # Arrange
        event1 = Event(slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2))
        event2 = Event(slug="2022-03-04-test", start=date(2022, 3, 4), end=date(2022, 3, 5))
        event3 = Event(slug="2022-05-01-test", start=date(2022, 5, 1), end=date(2022, 5, 2))
        events = [event1, event2, event3]
        event = Event(slug="2022-03-05-test1", start=date(2022, 3, 5), end=date(2022, 3, 6))
        # Act
        results = get_event_conflicts(events, event)
        # Assert
        self.assertEqual(results, [event2])

    def test_get_event_conflicts_no_start_or_end_dates(self) -> None:
        """Regression test for #2243."""
        # Arrange
        event1 = Event(slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2))
        event2 = Event(slug="2022-02-01-test", start=None, end=date(2022, 2, 2))
        event3 = Event(slug="2022-03-01-test", start=date(2022, 3, 1), end=None)
        event4 = Event(slug="2022-xx-xx-test", start=None, end=None)
        events = [event1, event2, event3, event4]
        event = Event(slug="2022-01-02-test", start=date(2022, 1, 2), end=date(2022, 1, 3))
        # Act
        results = get_event_conflicts(events, event)
        # Assert
        self.assertEqual(results, [event1])

    def test_get_events_nearby(self) -> None:
        # Arrange
        event1 = Event(slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2))
        event2 = Event(slug="2022-03-04-test", start=date(2022, 3, 4), end=date(2022, 3, 5))
        event3 = Event(slug="2022-05-01-test", start=date(2022, 5, 1), end=date(2022, 5, 2))
        events = [event1, event2, event3]
        event = Event(slug="2022-03-05-test1", start=date(2022, 3, 5), end=date(2022, 3, 6))
        # Act
        results = get_events_nearby(events, event, days_before=100)
        # Assert
        self.assertEqual(results, [event1, event2])

    def test_get_events_nearby_no_start_or_end_dates(self) -> None:
        """Regression test for #2243."""
        # Arrange
        event1 = Event(slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2))
        event2 = Event(slug="2022-02-01-test", start=None, end=date(2022, 2, 2))
        event3 = Event(slug="2022-03-01-test", start=date(2022, 3, 1), end=None)
        event4 = Event(slug="2022-xx-xx-test", start=None, end=None)
        events = [event1, event2, event3, event4]
        event = Event(slug="2021-12-22-test", start=date(2021, 12, 22), end=date(2021, 12, 23))
        # Act
        results = get_events_nearby(events, event)
        # Assert
        self.assertEqual(results, [event1])

    def test_get_signup_conflicts(self) -> None:
        # Arrange
        signup1 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(
                event=Event(slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2))
            )
        )
        signup2 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(
                event=Event(slug="2022-03-04-test", start=date(2022, 3, 4), end=date(2022, 3, 5))
            )
        )
        signup3 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(
                event=Event(slug="2022-05-01-test", start=date(2022, 5, 1), end=date(2022, 5, 2))
            )
        )
        signups = [signup1, signup2, signup3]
        recruitment = InstructorRecruitment(
            event=Event(slug="2022-03-05-test1", start=date(2022, 3, 5), end=date(2022, 3, 6))
        )
        # Act
        results = get_signup_conflicts(signups, recruitment)
        # Assert
        self.assertEqual(results, [signup2])

    def test_get_signup_conflicts_no_start_or_end_dates(self) -> None:
        """Regression test for #2243."""
        # Arrange
        signup1 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(
                event=Event(slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2))
            )
        )
        signup2 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(event=Event(slug="2022-02-01-test", start=None, end=date(2022, 2, 2)))
        )
        signup3 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(event=Event(slug="2022-03-01-test", start=date(2022, 3, 1), end=None))
        )
        signup4 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(event=Event(slug="2022-xx-xx-test", start=None, end=None))
        )
        signups = [signup1, signup2, signup3, signup4]
        recruitment = InstructorRecruitment(
            event=Event(slug="2022-01-02-test", start=date(2022, 1, 2), end=date(2022, 1, 3))
        )
        # Act
        results = get_signup_conflicts(signups, recruitment)
        # Assert
        self.assertEqual(results, [signup1])

    def test_priority_label__success(self) -> None:
        # Arrange
        values = [1, RecruitmentPriority.MEDIUM]
        expected = ["Low", "Medium"]
        # Act
        for value, expected_ in zip(values, expected, strict=False):
            # Assert
            self.assertEqual(priority_label(value), expected_)

    def test_priority_label__failure(self) -> None:
        # Arrange
        values = [10, "HIGH", "High", "text", None, "3"]
        # Act
        for value in values:
            # Assert
            with self.assertRaises(ValueError):
                priority_label(value)  # type: ignore[arg-type]
