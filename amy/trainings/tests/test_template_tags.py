from datetime import date

from django.test import TestCase

from trainings.models import Involvement
from workshops.models import Person, TrainingProgress, TrainingRequirement
from workshops.templatetags.training_progress import (
    progress_description,
    progress_label,
)


class TestProgressDescriptionTemplateTag(TestCase):
    def setUp(self):
        self.person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )

    def test_progress_description__basic(self):
        welcome, _ = TrainingRequirement.objects.get_or_create(name="Welcome Session")
        progress = TrainingProgress.objects.create(
            trainee=self.person, requirement=welcome, state="p"
        )
        created = progress.created_at
        # Act
        expected = (
            f'Passed Welcome Session<br/>on {created.strftime("%A %d %B %Y at %H:%M")}.'
        )
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)

    def test_progress_description__notes(self):
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
            "Failed Welcome Session<br/>"
            f'on {created.strftime("%A %d %B %Y at %H:%M")}.<br/>'
            "Notes: Notes from admin"
        )
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)

    def test_progress_description__get_involved(self):
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
        expected = (
            "Passed Get Involved<br/>"
            "GitHub Contribution<br/>"
            f'on {day.strftime("%A %d %B %Y")}.'
        )
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)

    def test_progress_description__get_involved__other(self):
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
        expected = (
            "Passed Get Involved<br/>"
            "Other: Notes from trainee<br/>"
            f'on {day.strftime("%A %d %B %Y")}.'
        )
        got = progress_description(progress)
        # Assert
        self.assertHTMLEqual(expected, got)


class TestProgressLabelTemplateTag(TestCase):
    def test_progress_labels(self):
        self.person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        welcome, _ = TrainingRequirement.objects.get_or_create(name="Welcome Session")

        expected = {
            "p": "badge bg-success",
            "f": "badge bg-danger",
            "a": "badge bg-info",
            "n": "badge bg-warning",
        }

        for state in expected.keys():
            progress = TrainingProgress.objects.create(
                trainee=self.person,
                requirement=welcome,
                state=state,
                notes="Notes from admin",
            )
            got = progress_label(progress)
            self.assertEqual(expected[state], got)
