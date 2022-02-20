from datetime import date

from django.test import TestCase

from dashboard.forms import SignupForRecruitmentForm
from recruitment.models import InstructorRecruitment
from workshops.models import Event, Organization, Person, Role, Task


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
