from datetime import date

from django.test import TestCase

from src.trainings.models import Involvement
from src.workshops.models import Person, TrainingProgress, TrainingRequirement
from src.workshops.templatetags.training_progress import (
    checkout_deadline,
    progress_description,
    progress_label,
)


class TestProgressDescriptionTemplateTag(TestCase):
    def setUp(self) -> None:
        self.person = Person.objects.create(personal="Test", family="User", email="test@user.com")

    def test_progress_description__basic(self) -> None:
        welcome, _ = TrainingRequirement.objects.get_or_create(name="Welcome Session")
        progress = TrainingProgress.objects.create(trainee=self.person, requirement=welcome, state="p")
        created = progress.created_at
        # Act
        expected = f"Passed Welcome Session<br/>on {created.strftime('%A %d %B %Y at %H:%M')}."
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)

    def test_progress_description__notes(self) -> None:
        welcome, _ = TrainingRequirement.objects.get_or_create(name="Welcome Session")
        progress = TrainingProgress.objects.create(
            trainee=self.person,
            requirement=welcome,
            state="f",
            notes="Notes from admin",
        )
        created = progress.created_at
        # Act
        expected = (
            f"Failed Welcome Session<br/>on {created.strftime('%A %d %B %Y at %H:%M')}.<br/>Notes: Notes from admin"
        )
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)

    def test_progress_description__get_involved(self) -> None:
        get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved", defaults={"involvement_required": True}
        )
        github_contribution, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution",
            defaults={"display_name": "GitHub Contribution", "url_required": True},
        )
        day = date(2023, 7, 11)
        progress = TrainingProgress.objects.create(
            trainee=self.person,
            requirement=get_involved,
            involvement_type=github_contribution,
            date=day,
            state="p",
        )
        # Act
        expected = f"Passed Get Involved<br/>GitHub Contribution<br/>on {day.strftime('%A %d %B %Y')}."
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)

    def test_progress_description__get_involved__other(self) -> None:
        get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved", defaults={"involvement_required": True}
        )
        involvement_other, _ = Involvement.objects.get_or_create(
            name="Other", defaults={"display_name": "Other", "notes_required": True}
        )
        day = date(2023, 7, 11)
        progress = TrainingProgress.objects.create(
            trainee=self.person,
            requirement=get_involved,
            involvement_type=involvement_other,
            trainee_notes="Notes from trainee",
            date=day,
            state="p",
        )
        # Act
        expected = f"Passed Get Involved<br/>Other: Notes from trainee<br/>on {day.strftime('%A %d %B %Y')}."
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)


class TestProgressLabelTemplateTag(TestCase):
    def test_progress_labels(self) -> None:
        self.person = Person.objects.create(personal="Test", family="User", email="test@user.com")
        welcome, _ = TrainingRequirement.objects.get_or_create(name="Welcome Session")

        expected = {
            "p": "badge badge-success",
            "f": "badge badge-danger",
            "a": "badge badge-info",
            "n": "badge badge-warning",
        }

        for state in expected:
            progress = TrainingProgress.objects.create(
                trainee=self.person,
                requirement=welcome,
                state=state,
                notes="Notes from admin",
            )
            got = progress_label(progress)
            self.assertEqual(expected[state], got)


class TestCheckoutDeadlineTemplateTag(TestCase):
    def test_checkout_deadline(self) -> None:
        # Arrange
        start = date(2023, 7, 25)
        # Act
        got = checkout_deadline(start)
        # Assert
        expected = date(2023, 10, 23)
        self.assertEqual(expected, got)
