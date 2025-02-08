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
        self.assertContains(rv, "If you have recently completed a training or step towards checkout")

    def test_progress_but_not_eligible(self):
        """Check the correct alert is displayed when some progress is completed."""
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=TrainingRequirement.objects.get(name="Welcome Session"),
            state="p",
        )
        rv = self.client.get(self.progress_url)
        self.assertNotContains(rv, "Congratulations, you're a certified Instructor!")
        self.assertContains(rv, "Please review your progress towards Instructor certification below.")

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
        workshop_instructor, _ = Involvement.objects.get_or_create(name="Workshop Instructor/Helper")
        for requirement in requirements:
            if requirement == "Get Involved":
                involvement = workshop_instructor
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

        admin = Person.objects.annotate_with_instructor_eligibility().get(username="admin")
        assert admin.get_missing_instructor_requirements() == []

        rv = self.client.get(self.progress_url)

        self.assertContains(
            rv,
            "You have successfully completed all steps towards Instructor " "certification",
        )

    def test_deadline_shown_when_training_passed(self):
        """Test that checkout deadline is displayed when trainee has passed training,
        but not completed all other steps."""
        self._setUpOrganizations()
        event = Event.objects.create(
            slug="event-ttt",
            start=date(2023, 6, 4),
            end=date(2023, 6, 5),
            host=self.org_alpha,
        )
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=TrainingRequirement.objects.get(name="Training"),
            event=event,
            state="p",
        )

        rv = self.client.get(self.progress_url)
        # check that the right if/else block is used
        self.assertContains(
            rv,
            "Please review your progress towards Instructor certification below.",
        )
        # check that the deadline is shown
        self.assertContains(
            rv,
            "Based on your training dates of",
        )

    def test_deadline_not_shown_when_training_not_passed(self):
        """Test that checkout deadline is displayed when trainee has passed training,
        but not completed all other steps."""
        self._setUpOrganizations()
        event = Event.objects.create(
            slug="event-ttt",
            start=date(2023, 6, 4),
            end=date(2023, 6, 5),
            host=self.org_alpha,
        )
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=TrainingRequirement.objects.get(name="Training"),
            event=event,
            state="f",
        )

        rv = self.client.get(self.progress_url)
        # check that the right if/else block is used
        self.assertContains(
            rv,
            "Please review your progress towards Instructor certification below.",
        )
        # check that no deadline is shown
        self.assertNotContains(
            rv,
            "Based on your training dates of",
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
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.training, event=self.event)
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Training <span class="badge-success">passed</span> ' "as of June 5, 2023.</p>",
            html=True,
        )

    def test_training_failed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.training, event=self.event, state="f")
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Training <span class="badge-danger">failed</span> ' "as of June 5, 2023.</p>",
            html=True,
        )

    def test_training_asked_to_repeat(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.training, event=self.event, state="a")
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Training <span class="badge-info">asked to repeat</span> ' "as of June 5, 2023.</p>",
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
        self.workshop_instructor, _ = Involvement.objects.get_or_create(
            name="Workshop Instructor/Helper",
            defaults={
                "display_name": "Served as an Instructor or a helper at a Carpentries " "workshop",
                "url_required": True,
            },
        )
        self.other_involvement, _ = Involvement.objects.get_or_create(
            name="Other", defaults={"display_name": "Other", "notes_required": True}
        )
        self.progress_url = reverse("training-progress")
        self.SESSION_LINK_TEXT = "Submit a Get Involved activity"

        self.progress = TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.workshop_instructor,
            date=datetime.today(),
            url="https://example.org",
            trainee_notes="Notes from trainee",
        )
        self.PROGRESS_SUMMARY_BLOCK = (
            "<p>"
            "<strong>Activity:</strong> Served as an Instructor or a helper at a "
            "Carpentries workshop<br/>"
            f'<strong>Date:</strong> {datetime.today().strftime("%B %-d, %Y")}<br/>'
            "<strong>URL:</strong> https://example.org<br/>"
            "<strong>Notes:</strong> Notes from trainee"
            "</p>"
        )
        self.EDIT_CLASS = "edit-object"  # class on the Edit button
        self.DELETE_CLASS = "delete-object"  # class on the Delete button

    def test_get_involved_not_submitted(self):
        # Arrange
        self.progress.delete()

        # Act
        rv = self.client.get(self.progress_url)

        # Assert
        self.assertContains(rv, "Get Involved step not submitted")
        self.assertContains(rv, self.SESSION_LINK_TEXT)

    def test_get_involved_waiting_to_be_evaluated(self):
        # Arrange
        self.progress.state = "n"
        self.progress.save()

        # Act
        rv = self.client.get(self.progress_url)

        # Assert
        self.assertContains(
            rv,
            '<p>Get Involved <span class="badge-warning">not evaluated yet</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertContains(rv, self.PROGRESS_SUMMARY_BLOCK, html=True)
        self.assertContains(rv, self.EDIT_CLASS)
        self.assertContains(rv, self.DELETE_CLASS)
        self.assertNotContains(rv, self.SESSION_LINK_TEXT, html=True)

    def test_get_involved_passed(self):
        # Arrange
        self.progress.state = "p"
        self.progress.save()

        # Act
        rv = self.client.get(self.progress_url)

        # Assert
        self.assertContains(
            rv,
            '<p>Get Involved <span class="badge-success">passed</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertContains(rv, self.PROGRESS_SUMMARY_BLOCK, html=True)
        self.assertNotContains(rv, self.EDIT_CLASS)
        self.assertNotContains(rv, self.DELETE_CLASS)
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_get_involved_failed(self):
        # Arrange
        self.progress.state = "f"
        self.progress.save()

        # Act
        rv = self.client.get(self.progress_url)

        # Assert
        self.assertContains(
            rv,
            '<p>Get Involved <span class="badge-danger">failed</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertContains(rv, self.PROGRESS_SUMMARY_BLOCK, html=True)
        self.assertNotContains(rv, self.EDIT_CLASS)
        self.assertNotContains(rv, self.DELETE_CLASS)
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_get_involved_asked_to_repeat(self):
        # Arrange
        self.progress.state = "a"
        self.progress.save()

        # Act
        rv = self.client.get(self.progress_url)

        # Assert
        self.assertContains(
            rv,
            '<p>Get Involved <span class="badge-info">asked to repeat</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertContains(rv, self.PROGRESS_SUMMARY_BLOCK, html=True)
        self.assertNotContains(rv, self.EDIT_CLASS)
        self.assertNotContains(rv, self.DELETE_CLASS)
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)
        self.assertContains(rv, "Submit another Get Involved activity")

    def test_get_involved_details_not_provided(self):
        """Check that optional fields are summarised correctly when empty"""
        # Arrange
        self.progress.delete()
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.workshop_instructor,
            state="n",
        )

        # Act
        rv = self.client.get(self.progress_url)

        # Assert
        PROGRESS_SUMMARY_BLOCK = (
            "<p>"
            "<strong>Activity:</strong> Served as an Instructor or a helper at a "
            "Carpentries workshop<br/>"
            "<strong>Date:</strong> No date provided<br/>"
            "<strong>URL:</strong> No URL provided<br/>"
            "<strong>Notes:</strong> No notes provided"
            "</p>"
        )
        self.assertContains(rv, PROGRESS_SUMMARY_BLOCK, html=True)


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
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.welcome, state="f")
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
        self.demo, _ = TrainingRequirement.objects.get_or_create(name="Demo", defaults={})
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
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.demo, state="a")
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Demo <span class="badge-info">asked to repeat</span> '
            f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertContains(rv, self.SESSION_LINK_TEXT)

    def test_session_failed(self):
        TrainingProgress.objects.create(trainee=self.admin, requirement=self.demo, state="f")
        rv = self.client.get(self.progress_url)
        self.assertContains(
            rv,
            '<p>Demo <span class="badge-danger">failed</span> ' f'as of {datetime.today().strftime("%B %-d, %Y")}.</p>',
            html=True,
        )
        self.assertNotContains(rv, self.SESSION_LINK_TEXT)

    def test_no_participation_in_a_session_yet(self):
        rv = self.client.get(self.progress_url)
        self.assertContains(rv, "Demo Session not completed")
        self.assertContains(rv, self.SESSION_LINK_TEXT)
