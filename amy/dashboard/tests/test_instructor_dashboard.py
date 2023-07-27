from datetime import date, datetime

from django.urls import reverse

from trainings.models import Involvement
from workshops.models import Award, Event, Person, TrainingProgress, TrainingRequirement
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

    def test_instructor_badge(self):
        """When the trainee is awarded a Carpentries Instructor badge,
        we want to display that info in the dashboard."""

        Award.objects.create(
            person=self.admin,
            badge=self.instructor_badge,
            awarded=datetime(2016, 6, 1, 15, 0),
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Congratulations, you're a certified Instructor!")
        self.assertIn(self.instructor_badge, rv.context["user"].instructor_badges)

    def test_not_an_instructor(self):
        """Check that we don't display that the trainee is an instructor if
        they don't have appropriate badge."""
        rv = self.client.get(self.progress_url)
        self.assertNotContains(rv, "Congratulations, you're a certified Instructor!")
        self.assertContains(
            rv, "If you have recently completed a training or step towards checkout"
        )

    def test_progress_but_not_eligible(self):
        """Check the correct alert is displayed when some progress is completed."""
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=TrainingRequirement.objects.get(name="Welcome Session"),
            state="p",
        )
        rv = self.client.get(self.progress_url)
        self.assertNotContains(rv, "Congratulations, you're a certified Instructor!")
        self.assertContains(
            rv, "Please review your progress towards Instructor certification below."
        )

    def test_eligible_but_not_awarded(self):
        """Test what is displayed when a trainee is eligible to be certified
        as an Instructor, but doesn't have appropriate badge awarded
        yet."""
        requirements = [
            "Training",
            "Get Involved",
            "Welcome Session",
            "Demo",
        ]
        for requirement in requirements:
            if requirement == "Get Involved":
                involvement = Involvement.objects.get(name="GitHub Contribution")
                date = datetime.today()
                url = "https://example.com"
            else:
                involvement = None
                date = None
                url = None
            TrainingProgress.objects.create(
                trainee=self.admin,
                requirement=TrainingRequirement.objects.get(name=requirement),
                involvement_type=involvement,
                date=date,
                url=url,
            )

        admin = Person.objects.annotate_with_instructor_eligibility().get(
            username="admin"
        )
        assert admin.get_missing_instructor_requirements() == []

        rv = self.client.get(self.progress_url)

        self.assertContains(
            rv,
            "You have successfully completed all steps towards Instructor "
            "certification",
        )


class TestInstructorTrainingStatus(TestBase):
    """Test that instructor dashboard displays status of passing Instructor
    Training."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpTags()
        self._setUpOrganizations()

        self.event = Event.objects.create(
            slug="event-ttt",
            start=date(2023, 6, 4),
            end=date(2023, 6, 5),
            host=self.org_alpha,
        )
        self.training = TrainingRequirement.objects.get(name="Training")
        self.progress_url = reverse("training-progress")

    def test_training_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, event=self.event
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Training <span class="badge-success">passed</span> '
            "as of June 5, 2023.</p>",
            html=True,
        )

    def test_training_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, event=self.event, state="f"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Training <span class="badge-danger">failed</span> '
            "as of June 5, 2023.</p>",
            html=True,
        )

    def test_training_asked_to_repeat(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, event=self.event, state="a"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Training <span class="badge-info">asked to repeat</span> '
            "as of June 5, 2023.</p>",
            html=True,
        )

    def test_training_not_finished(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Training not completed yet")


class TestGetInvolvedStatus(TestBase):
    """Test that trainee dashboard displays status of passing Get Involved.
    Test that Get Involved submission form works."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved", defaults={"involvement_required": True}
        )
        self.github_contribution, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution", defaults={"url_required": True}
        )
        self.other_involvement, _ = Involvement.objects.get_or_create(
            name="Other", defaults={"display_name": "Other", "notes_required": True}
        )
        self.progress_url = reverse("training-progress")

    def test_get_involved_not_submitted(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Get Involved step not submitted")

    def test_get_involved_waiting_to_be_evaluated(self):
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            state="n",
            involvement_type=self.github_contribution,
            date=datetime.today(),
            url="https://example.org",
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Get Involved <span class="badge-warning">not evaluated yet</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )

    def test_get_involved_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=datetime.today(),
            url="https://example.org",
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Get Involved <span class="badge-success">passed</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )

    def test_submission_form(self):
        data = {
            "url": "http://example.com",
            "requirement": self.get_involved.pk,
            "involvement_type": self.github_contribution.pk,
            "date": "2023-06-21",
        }
        rv = self.client.post(self.progress_url, data, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training-progress")
        self.assertContains(
            rv, "Your Get Involved submission will be reviewed within 7-10 days."
        )
        got = list(
            TrainingProgress.objects.values_list(
                "state", "trainee", "url", "requirement", "involvement_type", "date"
            )
        )
        expected = [
            (
                "n",
                self.admin.pk,
                "http://example.com",
                self.get_involved.pk,
                self.github_contribution.pk,
                date(2023, 6, 21),
            )
        ]
        self.assertEqual(got, expected)

    def test_submission_form_invalid_notes(self):
        """Test that errors relating to notes/trainee_notes fields are
        handled correctly."""
        data = {
            "requirement": self.get_involved.pk,
            "involvement_type": self.other_involvement.pk,
            "date": "2023-06-21",
        }
        rv = self.client.post(self.progress_url, data, follow=True)
        # if "notes" field error is not excluded, a server error will occur
        # as there is no "notes" field on the form
        # so a status code 200 means it has been excluded correctly
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training-progress")
        # check that "trainee_notes" field error is displayed
        # special treatment needed due to quotation marks
        self.assertContains(
            rv,
            'This field is required for activity "Other".',
            html=True,
        )
        # no TrainingProgress should have been created
        self.assertEqual(len(TrainingProgress.objects.all()), 0)


class TestWelcomeSessionStatus(TestBase):
    """Test that trainee dashboard displays status of passing Welcome
    Session. Test whether we display instructions for registering for a
    session."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.welcome = TrainingRequirement.objects.get(name="Welcome Session")
        self.progress_url = reverse("training-progress")
        self.SESSION_LINK_TEXT = "Register for a Welcome Session on"

    def test_session_passed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.welcome)
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Welcome Session <span class="badge-success">completed</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_session_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.welcome, state="f"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Welcome Session <span class="badge-danger">failed</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_no_participation_in_a_session_yet(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Welcome Session not completed yet")
        self.assertContains(rv, self.SESSION_LINK_TEXT)


class TestDemoSessionStatus(TestBase):
    """Test that trainee dashboard displays status of passing a Demo Session. Test
    whether we display instructions for registering for a session."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.demo, _ = TrainingRequirement.objects.get_or_create(
            name="Demo", defaults={}
        )
        self.progress_url = reverse("training-progress")
        self.SESSION_LINK_TEXT = "Register for a Demo Session on"

    def test_session_passed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.demo)
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Demo <span class="badge-success">passed</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_session_asked_to_repeat(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.demo, state="a"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Demo <span class="badge-info">asked to repeat</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertContains(rv, self.SESSION_LINK_TEXT)

    def test_session_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.demo, state="f"
        )
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Demo <span class="badge-danger">failed</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_no_participation_in_a_session_yet(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Demo Session not completed")
        self.assertContains(rv, self.SESSION_LINK_TEXT)
