from datetime import date

from django.conf import settings
from django.test import TestCase, override_settings

from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from recruitment.templatetags.instructorrecruitment import (
    get_event_conflicts,
    get_events_nearby,
    get_signup_conflicts,
    is_instructor_recruitment_enabled,
)
from workshops.models import Event


class TestInstructorRecruitmentTemplateTags(TestCase):
    def test_feature_flag_enabled(self) -> None:
        with self.settings(INSTRUCTOR_RECRUITMENT_ENABLED=False):
            self.assertEqual(is_instructor_recruitment_enabled(), False)
        with self.settings(INSTRUCTOR_RECRUITMENT_ENABLED=True):
            self.assertEqual(is_instructor_recruitment_enabled(), True)

    @override_settings()
    def test_feature_flag_removed(self) -> None:
        del settings.INSTRUCTOR_RECRUITMENT_ENABLED

        self.assertEqual(is_instructor_recruitment_enabled(), False)

    def test_get_event_conflicts(self) -> None:
        # Arrange
        event1 = Event(
            slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2)
        )
        event2 = Event(
            slug="2022-03-04-test", start=date(2022, 3, 4), end=date(2022, 3, 5)
        )
        event3 = Event(
            slug="2022-05-01-test", start=date(2022, 5, 1), end=date(2022, 5, 2)
        )
        events = [event1, event2, event3]
        event = Event(
            slug="2022-03-05-test1", start=date(2022, 3, 5), end=date(2022, 3, 6)
        )
        # Act
        results = get_event_conflicts(events, event)
        # Assert
        self.assertEqual(results, [event2])

    def test_get_events_nearby(self) -> None:
        # Arrange
        event1 = Event(
            slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2)
        )
        event2 = Event(
            slug="2022-03-04-test", start=date(2022, 3, 4), end=date(2022, 3, 5)
        )
        event3 = Event(
            slug="2022-05-01-test", start=date(2022, 5, 1), end=date(2022, 5, 2)
        )
        events = [event1, event2, event3]
        event = Event(
            slug="2022-03-05-test1", start=date(2022, 3, 5), end=date(2022, 3, 6)
        )
        # Act
        results = get_events_nearby(events, event, days_before=100)
        # Assert
        self.assertEqual(results, [event1, event2])

    def test_get_signup_conflicts(self) -> None:
        # Arrange
        signup1 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(
                event=Event(
                    slug="2022-01-01-test", start=date(2022, 1, 1), end=date(2022, 1, 2)
                )
            )
        )
        signup2 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(
                event=Event(
                    slug="2022-03-04-test", start=date(2022, 3, 4), end=date(2022, 3, 5)
                )
            )
        )
        signup3 = InstructorRecruitmentSignup(
            recruitment=InstructorRecruitment(
                event=Event(
                    slug="2022-05-01-test", start=date(2022, 5, 1), end=date(2022, 5, 2)
                )
            )
        )
        signups = [signup1, signup2, signup3]
        recruitment = InstructorRecruitment(
            event=Event(
                slug="2022-03-05-test1", start=date(2022, 3, 5), end=date(2022, 3, 6)
            )
        )
        # Act
        results = get_signup_conflicts(signups, recruitment)
        # Assert
        self.assertEqual(results, [signup2])
