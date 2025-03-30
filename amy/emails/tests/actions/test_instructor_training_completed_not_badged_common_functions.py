from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.instructor_training_completed_not_badged import (
    get_context,
    get_generic_relation_object,
    get_recipients,
    get_scheduled_at,
)
from emails.types import InstructorTrainingCompletedNotBadgedContext
from workshops.models import Person, TrainingProgress, TrainingRequirement


class TestInstructorTrainingCompletedNotBadgedCommonFunctions(TestCase):
    def setUpTrainingProgresses(self, person: Person) -> None:
        self.requirements = TrainingRequirement.objects.filter(
            name__in=["Training", "Get Involved", "Welcome Session", "Demo"]
        )
        self.progresses = [
            TrainingProgress(state="p", trainee=person, requirement=self.requirements[0]),
            TrainingProgress(state="f", trainee=person, requirement=self.requirements[1]),
            TrainingProgress(state="a", trainee=person, requirement=self.requirements[2]),
            # Last requirement is left ungraded.
            # TrainingProgress(state="p", trainee=person, requirement=requirements[3]),
        ]
        TrainingProgress.objects.bulk_create(self.progresses)

    def setUpContext(
        self, person: Person, training_completed_date: datetime
    ) -> InstructorTrainingCompletedNotBadgedContext:
        return {
            "person": person,
            "passed_requirements": [self.progresses[0]],
            "not_passed_requirements": [self.progresses[1], self.progresses[2]],
            "not_graded_requirements": [self.requirements[3]],
            "training_completed_date": training_completed_date,
            "certification_deadline": training_completed_date + timedelta(days=3 * 30),
        }

    @patch("emails.utils.datetime", wraps=datetime)
    def test_get_scheduled_at(self, mock_datetime: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        person = Person()
        training_completed_date = datetime(2023, 1, 1)
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        scheduled_at = get_scheduled_at(
            request=request,
            person=person,
            training_completed_date=training_completed_date,
        )

        # Assert
        self.assertEqual(scheduled_at, datetime(2023, 3, 2, 12, 0, 0, tzinfo=UTC))

    def test_get_context(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(username="test")
        training_completed_date = datetime.now()
        self.setUpTrainingProgresses(person)

        # Act
        context = get_context(
            request=request,
            person=person,
            training_completed_date=training_completed_date,
        )

        # Assert
        self.assertEqual(
            context,
            {
                "person": person,
                "passed_requirements": [self.progresses[0]],
                "not_passed_requirements": [self.progresses[1], self.progresses[2]],
                "not_graded_requirements": [self.requirements[3]],
                "training_completed_date": training_completed_date,
                "certification_deadline": training_completed_date + timedelta(days=3 * 30),
            },
        )

    def test_get_generic_relation_object(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(username="test")
        training_completed_date = datetime.now()
        self.setUpTrainingProgresses(person)

        # Act
        obj = get_generic_relation_object(
            context=self.setUpContext(person, training_completed_date),
            request=request,
            person=person,
            training_completed_date=training_completed_date,
        )

        # Assert
        self.assertEqual(obj, person)

    def test_get_recipients(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(username="test", email="test@example.org")
        training_completed_date = datetime.now()
        self.setUpTrainingProgresses(person)

        # Act
        obj = get_recipients(
            context=self.setUpContext(person, training_completed_date),
            request=request,
            person=person,
            training_completed_date=training_completed_date,
        )

        # Assert
        self.assertEqual(obj, [person.email])

    def test_get_recipients__no_email(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(username="test")  # no email for this person
        training_completed_date = datetime.now()
        self.setUpTrainingProgresses(person)

        # Act
        obj = get_recipients(
            context=self.setUpContext(person, training_completed_date),
            request=request,
            person=person,
            training_completed_date=training_completed_date,
        )

        # Assert
        self.assertEqual(obj, [])
