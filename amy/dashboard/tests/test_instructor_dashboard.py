from datetime import datetime

from django.urls import reverse

from workshops.models import Award, Person, TrainingProgress, TrainingRequirement
from workshops.tests.base import TestBase


class TestInstructorDashboard(TestBase):
    """Tests for instructor dashboard."""

    def setUp(self):
        self.user = Person.objects.create_user(
            username="user",
            personal="",
            family="",
            email="user@example.org",
            password="pass",
        )
        self.person_consent_required_terms(self.user)
        self.client.login(username="user", password="pass")

    def test_dashboard_loads(self):
        rv = self.client.get(reverse("instructor-dashboard"))
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode("utf-8")
        self.assertIn("Log out", content)
        self.assertIn("Update your profile", content)


class TestInstructorStatus(TestBase):
    """Test that instructor dashboard displays information about awarded SWC/DC
    Instructor badges."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpBadges()
        self.progress_url = reverse("training-progress")
        TrainingRequirement.objects.create(
            name="Lesson Contribution", url_required=True
        )
        TrainingRequirement.objects.create(name="Demo")

    def test_instructor_badge(self):
        """When the trainee is awarded both Carpentry Instructor badge,
        we want to display that info in the dashboard."""

        Award.objects.create(
            person=self.admin,
            badge=self.instructor_badge,
            awarded=datetime(2016, 6, 1, 15, 0),
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Congratulations, you're a certified")
        self.assertIn(self.instructor_badge, rv.context["user"].instructor_badges)

    def test_neither_swc_nor_dc_instructor(self):
        """Check that we don't display that the trainee is an instructor if
        they don't have appropriate badge."""
        rv = self.client.get(self.progress_url)
        self.assertNotContains(rv, "Congratulations, you're certified")

    def test_eligible_but_not_awarded(self):
        """Test what is dispslayed when a trainee is eligible to be certified
        as an SWC/DC Instructor, but doesn't have appropriate badge awarded
        yet."""
        requirements = [
            "Training",
            "Lesson Contribution",
            "Discussion",
            "Demo",
        ]
        for requirement in requirements:
            TrainingProgress.objects.create(
                trainee=self.admin,
                requirement=TrainingRequirement.objects.get(name=requirement),
            )

        admin = Person.objects.annotate_with_instructor_eligibility().get(
            username="admin"
        )
        assert admin.get_missing_instructor_requirements() == []

        rv = self.client.get(self.progress_url)

        self.assertNotContains(rv, "Congratulations, you're certified")


class TestInstructorTrainingStatus(TestBase):
    """Test that instructor dashboard displays status of passing Instructor
    Training."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.training = TrainingRequirement.objects.get(name="Training")
        self.progress_url = reverse("training-progress")

    def test_training_passed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.training)
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Training passed")

    def test_training_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, discarded=True
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Training not passed yet")

    def test_last_training_discarded_but_another_is_passed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.training)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, discarded=True
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Training passed")

    def test_training_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, state="f"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Training not passed yet")

    def test_training_asked_to_repeat(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, state="a"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Training not passed yet")

    def test_training_not_finished(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Training not passed yet")


class TestLessonContributionStatus(TestBase):
    """Test that trainee dashboard displays status of passing Lesson Contribution.
    Test that Lesson Contribution submission form works."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.lesson_contribution, _ = TrainingRequirement.objects.get_or_create(
            name="Lesson Contribution", defaults={"url_required": True}
        )
        self.progress_url = reverse("training-progress")

    def test_lesson_contribution_not_submitted(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Lesson Contribution not submitted")

    def test_lesson_contribution_waiting_to_be_evaluated(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.lesson_contribution, state="n"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Lesson Contribution evaluation pending")

    def test_lesson_contribution_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.lesson_contribution
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Lesson Contribution accepted")

    def test_lesson_contribution_not_accepted_when_lesson_contribution_passed_but_discarded(  # noqa: line too long
        self,
    ):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.lesson_contribution, discarded=True
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Lesson Contribution not submitted")

    def test_lesson_contribution_is_accepted_when_last_lesson_contribution_is_discarded_but_other_one_is_passed(  # noqa: line too long
        self,
    ):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.lesson_contribution
        )
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.lesson_contribution, discarded=True
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Lesson Contribution accepted")

    def test_submission_form(self):
        data = {
            "url": "http://example.com",
            "requirement": self.lesson_contribution.pk,
        }
        rv = self.client.post(self.progress_url, data, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training-progress")
        self.assertContains(
            rv, "Your Lesson Contribution submission will be evaluated soon."
        )
        got = list(
            TrainingProgress.objects.values_list(
                "state", "trainee", "url", "requirement"
            )
        )
        expected = [
            (
                "n",
                self.admin.pk,
                "http://example.com",
                self.lesson_contribution.pk,
            )
        ]
        self.assertEqual(got, expected)


class TestDiscussionSessionStatus(TestBase):
    """Test that trainee dashboard displays status of passing Discussion
    Session. Test whether we display instructions for registering for a
    session."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.discussion = TrainingRequirement.objects.get(name="Discussion")
        self.progress_url = reverse("training-progress")

    def test_session_passed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.discussion)
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Discussion Session passed")

    def test_session_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion, discarded=True
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Discussion Session not passed yet")

    def test_last_session_discarded_but_another_is_passed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.discussion)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion, discarded=True
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Discussion Session passed")

    def test_session_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion, state="f"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Discussion Session not passed yet")

    def test_no_participation_in_a_session_yet(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Discussion Session not passed yet")


class TestDemoSessionStatus(TestBase):
    """Test that trainee dashboard displays status of passing a Demo Session. Test
    whether we display instructions for registering for a session."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.demo, _ = TrainingRequirement.objects.get_or_create(
            name="Demo", defaults={}
        )
        self.progress_url = reverse("training-progress")
        self.SESSION_LINK_TEXT = "You can register for a Demo Session on"

    def test_session_passed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.demo)
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Demo Session passed")
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_session_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.demo, discarded=True
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Demo Session not completed")
        self.assertContains(rv, self.SESSION_LINK_TEXT)

    def test_session_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.demo, state="f"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Demo Session not completed")
        self.assertContains(rv, self.SESSION_LINK_TEXT)

    def test_no_participation_in_a_session_yet(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Demo Session not completed")
        self.assertContains(rv, self.SESSION_LINK_TEXT)

    def test_no_registration_instruction_when_trainee_passed_session(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.demo)
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Demo Session passed")
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)
