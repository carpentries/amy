from datetime import date, datetime

from django.test import TestCase

from trainings.models import Involvement
from workshops.models import Event, Person, Tag, TrainingProgress, TrainingRequirement
from workshops.templatetags.training_progress import (
    checkout_deadline,
    progress_description,
    progress_label,
    progress_trainee_view,
)
from workshops.tests.base import TestBase


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
            "p": "badge badge-success",
            "f": "badge badge-danger",
            "a": "badge badge-info",
            "n": "badge badge-warning",
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


class TestCheckoutDeadlineTemplateTag(TestCase):
    def test_checkout_deadline(self):
        # Arrange
        start = date(2023, 7, 25)
        # Act
        got = checkout_deadline(start)
        # Assert
        expected = date(2023, 10, 23)
        self.assertEqual(expected, got)


class TestProgressTraineeViewTemplateTag(TestBase):
    def test_progress_trainee_view__training(self):
        # Arrange
        self._setUpTags()
        event = Event.objects.create(
            slug="event-ttt",
            start=date(2023, 6, 24),
            end=date(2023, 6, 25),
            host=self.org_alpha,
        )
        event.tags.add(Tag.objects.get(name="TTT"))
        requirement, _ = TrainingRequirement.objects.get_or_create(name="Training")
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=requirement,
            state="p",  # passed
            event=event,
            url=None,
        )

        # Act
        got = progress_trainee_view(progress)

        # Assert
        expected = '<p class="text-success"> Training passed as of June 25, 2023.</p>'
        self.assertHTMLEqual(expected, got)

    def test_progress_trainee_view__get_involved(self):
        # Arrange
        requirement, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved", defaults={"involvement_required": True}
        )
        involvement, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution", defaults={"url_required": True}
        )
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=requirement,
            involvement_type=involvement,
            state="p",  # passed
            event=None,
            url="https://example.org",
            date=date(2023, 6, 25),
        )

        # Act
        got = progress_trainee_view(progress)

        # Assert
        expected = (
            '<p class="text-success"> Get Involved passed as of '
            f'{datetime.today().strftime("%B %d, %Y")}.</p>'
        )
        self.assertHTMLEqual(expected, got)

    def test_progress_trainee_view__welcome(self):
        # Arrange
        requirement, _ = TrainingRequirement.objects.get_or_create(
            name="Welcome Session"
        )
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=requirement,
            state="p",  # passed
        )

        # Act
        got = progress_trainee_view(progress)

        # Assert
        expected = (
            '<p class="text-success"> Welcome Session completed as of '
            f'{datetime.today().strftime("%B %d, %Y")}.</p>'
        )
        self.assertHTMLEqual(expected, got)

    def test_progress_trainee_view__demo(self):
        # Arrange
        requirement, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=requirement,
            state="p",  # passed
        )

        # Act
        got = progress_trainee_view(progress)

        # Assert
        expected = (
            '<p class="text-success"> Demo passed as of '
            f'{datetime.today().strftime("%B %d, %Y")}.</p>'
        )
        self.assertHTMLEqual(expected, got)

    def test_progress_trainee_view__failed(self):
        # Arrange
        requirement, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=requirement,
            state="f",  # failed
            notes="Reason for failure",
        )

        # Act
        got = progress_trainee_view(progress)

        # Assert
        expected = (
            '<p class="text-danger"> Demo failed as of '
            f'{datetime.today().strftime("%B %d, %Y")}.</p>'
            "<p>Administrator comments: Reason for failure</p>"
        )
        self.assertHTMLEqual(expected, got)

    def test_progress_trainee_view__asked_to_repeat(self):
        # Arrange
        requirement, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=requirement,
            state="a",  # asked to repeat
            notes="Reason for asking to repeat",
        )

        # Act
        got = progress_trainee_view(progress)

        # Assert
        expected = (
            '<p class="text-info"> Demo asked to repeat as of '
            f'{datetime.today().strftime("%B %d, %Y")}.</p>'
            "<p>Administrator comments: Reason for asking to repeat</p>"
        )
        self.assertHTMLEqual(expected, got)

    def test_progress_trainee_view__not_evaluated_yet(self):
        # Arrange
        requirement, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=requirement,
            state="n",  # not evaluated yet
        )

        # Act
        got = progress_trainee_view(progress)

        # Assert
        expected = (
            '<p class="text-warning"> Demo not evaluated yet as of '
            f'{datetime.today().strftime("%B %d, %Y")}.</p>'
        )
        self.assertHTMLEqual(expected, got)
