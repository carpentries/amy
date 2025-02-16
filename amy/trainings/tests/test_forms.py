from trainings.forms import TrainingProgressForm
from workshops.models import (
    Event,
    Organization,
    Person,
    Role,
    Tag,
    Task,
    TrainingRequirement,
)
from workshops.tests.base import TestBase


class TestTrainingProgressForm(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpTags()
        self._setUpRoles()

        self.training, _ = TrainingRequirement.objects.get_or_create(name="Training", defaults={"event_required": True})

        host = Organization.objects.create(domain="test.com", fullname="Test")
        self.person = Person.objects.create(personal="Test", family="User", email="test@user.com")
        self.ttt_event = Event.objects.create(slug="test-event", host=host)
        self.ttt_event.tags.add(Tag.objects.get(name="TTT"))

    def test_fields(self):
        # Act
        form = TrainingProgressForm()

        # Assert
        self.assertEqual(
            {
                "trainee",
                "requirement",
                "state",
                "involvement_type",
                "event",
                "url",
                "date",
                "trainee_notes",
                "notes",
            },
            form.fields.keys(),
        )

    def test_clean_custom_validation__no_learner_task(self):
        # Arrange
        data = {
            "trainee": self.person,
            "state": "p",
            "requirement": self.training,
            "event": self.ttt_event,
        }

        # Act
        form = TrainingProgressForm(data)

        # Assert
        self.assertEqual(form.is_valid(), False)
        expected_msg = (
            "This progress cannot be created without a corresponding learner "
            f"task. Trainee {self.person} does not have a learner task for "
            f"event {self.ttt_event}."
        )
        self.assertEqual(
            form.errors["event"],
            [expected_msg],
        )

    def test_clean_custom_validation__learner_task_present(self):
        # Arrange
        data = {
            "trainee": self.person,
            "state": "p",
            "requirement": self.training,
            "event": self.ttt_event,
        }
        Task.objects.create(
            person=self.person,
            event=self.ttt_event,
            role=Role.objects.get(name="learner"),
        )

        # Act
        form = TrainingProgressForm(data)

        # Assert
        self.assertEqual(form.is_valid(), True)
