from datetime import date

from django.test import TestCase

from dashboard.forms import GetInvolvedForm, SignupForRecruitmentForm
from recruitment.models import InstructorRecruitment
from trainings.models import Involvement
from workshops.models import (
    Event,
    Organization,
    Person,
    Role,
    Task,
    TrainingProgress,
    TrainingRequirement,
)


class TestSignupForRecruitmentForm(TestCase):
    def test_required_init_params(self):
        # Arrange
        host = Organization(domain="test.com", fullname="Test")
        person = Person(personal="Test", family="User", email="test@user.com")
        event = Event(slug="test-event", host=host)
        recruitment = InstructorRecruitment(status="o", event=event)

        # Act & Assert
        # - person required
        with self.assertRaises(KeyError):
            SignupForRecruitmentForm()
        # - recruitment required
        with self.assertRaises(KeyError):
            SignupForRecruitmentForm(person=person)
        # - person & recruitment required
        SignupForRecruitmentForm(person=person, recruitment=recruitment)

    def test_fields(self):
        # Arrange
        host = Organization(domain="test.com", fullname="Test")
        person = Person(personal="Test", family="User", email="test@user.com")
        event = Event(slug="test-event", host=host)
        recruitment = InstructorRecruitment(status="o", event=event)

        # Act
        form = SignupForRecruitmentForm(person=person, recruitment=recruitment)

        # Assert
        self.assertEqual({"user_notes"}, form.fields.keys())

    def test_clean_custom_validation__no_dates_event(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(slug="test-event", host=host)  # no dates
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        data = {}

        # Act
        form = SignupForRecruitmentForm(data, person=person, recruitment=recruitment)

        # Assert
        self.assertEqual(form.is_valid(), True)

    def test_clean_custom_validation__no_conflicting_tasks(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        data = {}

        # Act
        form = SignupForRecruitmentForm(data, person=person, recruitment=recruitment)

        # Assert
        self.assertEqual(form.is_valid(), True)

    def test_clean_custom_validation__conflicting_tasks(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        event2 = Event.objects.create(
            slug="test2-event",
            host=host,
            start=date(2022, 2, 18),  # dates are overlapping with test-event
            end=date(2022, 2, 19),
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        instructor_role = Role.objects.create(name="instructor")
        conflicting_task = Task.objects.create(
            event=event2, person=person, role=instructor_role
        )
        data = {}

        # Act
        form = SignupForRecruitmentForm(data, person=person, recruitment=recruitment)

        # Assert
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors["__all__"],
            [
                "Selected event dates conflict with events: "
                f"{conflicting_task.event.slug}"
            ],
        )


class TestGetInvolvedForm(TestCase):
    def setUp(self):
        super().setUp()
        self.person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        self.get_involved = TrainingRequirement.objects.get(name="Get Involved")

        self.involvement, _ = Involvement.objects.get_or_create(
            name="Other", defaults={"display_name": "Other", "notes_required": True}
        )
        self.base_instance = TrainingProgress(
            trainee=self.person,
            state="n",  # not evaluated yet
            requirement=TrainingRequirement.objects.get(name="Get Involved"),
        )
        self.EXISTING_SUBMISSION_ERROR_TEXT = (
            "You already have an existing submission. "
            "You may not create another submission unless your previous "
            'submission has the status "asked to repeat."'
        )
        self.ALREADY_EVALUATED_ERROR_TEXT = (
            "This submission can no longer be edited as it has already been evaluated."
        )

    def test_fields(self):
        # Act
        form = GetInvolvedForm()

        # Assert
        self.assertEqual(
            {"involvement_type", "date", "url", "trainee_notes"}, form.fields.keys()
        )

    def test_clean_custom_validation__trainee_notes(self):
        # Arrange
        data = {"involvement_type": self.involvement, "date": date(2023, 7, 27)}

        # Act
        form = GetInvolvedForm(data, instance=self.base_instance)

        # Assert
        # expect to see an error on "trainee_notes" and not on "notes"
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors["trainee_notes"],
            ['This field is required for activity "Other".'],
        )
        self.assertNotIn("notes", form.errors.keys())

    def test_clean_custom_validation__no_involvement_type(self):
        """Check that trainee_notes validation works when no involvement is chosen"""
        # Arrange
        data = {}

        # Act
        form = GetInvolvedForm(data, instance=self.base_instance)

        # Assert
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors["involvement_type"],
            ['This field is required for progress type "Get Involved".'],
        )
        self.assertNotIn("trainee_notes", form.errors.keys())

    def test_custom_validation__existing_not_evaluated_yet(self):
        # Arrange
        # create pre-existing submission
        TrainingProgress.objects.create(
            trainee=self.person,
            requirement=self.get_involved,
            involvement_type=self.involvement,
            date=date(2023, 7, 1),
            trainee_notes="Notes from trainee",
            state="n",
        )
        data = {
            "involvement_type": self.involvement,
            "trainee_notes": "Notes from trainee",
            "date": date(2023, 7, 27),
        }

        # Act
        form = GetInvolvedForm(data, instance=self.base_instance)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors["__all__"],
            [self.EXISTING_SUBMISSION_ERROR_TEXT],
        )

    def test_custom_validation__existing_passed(self):
        # Arrange
        # create pre-existing submission
        TrainingProgress.objects.create(
            trainee=self.person,
            requirement=self.get_involved,
            involvement_type=self.involvement,
            date=date(2023, 7, 1),
            trainee_notes="Notes from trainee",
            state="p",
        )
        data = {
            "involvement_type": self.involvement,
            "trainee_notes": "Notes from trainee",
            "date": date(2023, 7, 27),
        }

        # Act
        form = GetInvolvedForm(data, instance=self.base_instance)

        # Assert
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors["__all__"],
            [self.EXISTING_SUBMISSION_ERROR_TEXT],
        )

    def test_custom_validation__existing_failed(self):
        # Arrange
        # create pre-existing submission
        TrainingProgress.objects.create(
            trainee=self.person,
            requirement=self.get_involved,
            involvement_type=self.involvement,
            date=date(2023, 7, 1),
            trainee_notes="Notes from trainee",
            state="f",
        )
        data = {
            "involvement_type": self.involvement,
            "trainee_notes": "Notes from trainee",
            "date": date(2023, 7, 27),
        }

        # Act
        form = GetInvolvedForm(data, instance=self.base_instance)

        # Assert
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors["__all__"],
            [self.EXISTING_SUBMISSION_ERROR_TEXT],
        )

    def test_custom_validation__existing_asked_to_repeat(self):
        # Arrange
        # create pre-existing submission
        TrainingProgress.objects.create(
            trainee=self.person,
            requirement=self.get_involved,
            involvement_type=self.involvement,
            date=date(2023, 7, 1),
            trainee_notes="Notes from trainee",
            state="a",
        )
        data = {
            "involvement_type": self.involvement,
            "trainee_notes": "Notes from trainee",
            "date": date(2023, 7, 27),
        }

        # Act
        form = GetInvolvedForm(data, instance=self.base_instance)

        # Assert
        self.assertEqual(form.is_valid(), True)

    def test_custom_validation__already_evaluated(self):
        # Arrange
        # create pre-existing submission
        progress = TrainingProgress.objects.create(
            trainee=self.person,
            requirement=self.get_involved,
            involvement_type=self.involvement,
            date=date(2023, 7, 1),
            trainee_notes="Notes from trainee",
            state="p",
        )
        data = {
            "involvement_type": self.involvement,
            "trainee_notes": "Updated notes from trainee",
            "date": date(2023, 7, 27),
        }

        # Act
        form = GetInvolvedForm(data, instance=progress)

        # Assert
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors["__all__"],
            [self.ALREADY_EVALUATED_ERROR_TEXT],
        )

    def test_custom_validation__not_already_evaluated(self):
        # Arrange
        # create pre-existing submission
        progress = TrainingProgress.objects.create(
            trainee=self.person,
            requirement=self.get_involved,
            involvement_type=self.involvement,
            date=date(2023, 7, 1),
            trainee_notes="Notes from trainee",
            state="n",
        )
        data = {
            "involvement_type": self.involvement,
            "trainee_notes": "Updated notes from trainee",
            "date": date(2023, 7, 27),
        }

        # Act
        form = GetInvolvedForm(data, instance=progress)

        # Assert
        self.assertEqual(form.is_valid(), True)
