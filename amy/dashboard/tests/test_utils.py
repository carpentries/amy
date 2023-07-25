from dashboard.utils import get_passed_or_last_progress
from workshops.models import TrainingProgress, TrainingRequirement
from workshops.tests.base import TestBase


class TestGetLastOrPassedProgress(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpTags()

        # set up some progresses
        self.requirement, _ = TrainingRequirement.objects.get_or_create(name="Demo")

    def test_no_progress(self):
        """Should return None if no progress present."""
        # Act
        got_progress = get_passed_or_last_progress(
            self.spiderman, self.requirement.name
        )
        # Assert
        self.assertIsNone(got_progress)

    def test_single_passed_progress(self):
        """Only one progress, and it's passed"""
        # Arrange
        expected = TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="p"
        )
        # Act
        got_progress = get_passed_or_last_progress(
            self.spiderman, self.requirement.name
        )
        # Assert
        self.assertEqual(expected, got_progress)

    def test_single_nonpassed_progress(self):
        """Only one progress, and it's not passed"""
        # Arrange
        expected = TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="f"
        )
        # Act
        got_progress = get_passed_or_last_progress(
            self.spiderman, self.requirement.name
        )
        # Assert
        self.assertEqual(expected, got_progress)

    def test_passed_progress_prioritised(self):
        """Passed progress should be returned even if later progresses exist"""
        # Arrange
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="a"
        )
        expected = TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="p"
        )
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="f"
        )
        # Act
        got_progress = get_passed_or_last_progress(
            self.spiderman, self.requirement.name
        )
        # Assert
        self.assertEqual(expected, got_progress)

    def test_recent_progress_no_pass(self):
        """The most recent progress should be returned if none are passed"""
        # Arrange
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="a"
        )
        expected = TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="a"
        )
        # Act
        got_progress = get_passed_or_last_progress(
            self.spiderman, self.requirement.name
        )
        # Assert
        self.assertEqual(expected, got_progress)

    def test_recent_passed_progress(self):
        """The most recent passed progress should be returned if multiple are passed"""
        # Arrange
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="p"
        )
        expected = TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.requirement, state="p"
        )
        # Act
        got_progress = get_passed_or_last_progress(
            self.spiderman, self.requirement.name
        )
        # Assert
        self.assertEqual(expected, got_progress)
