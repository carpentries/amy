from datetime import date, timedelta
from unittest.mock import patch

from django.test import RequestFactory, override_settings
from django.urls import reverse

from emails.actions.instructor_training_completed_not_badged import (
    instructor_training_completed_not_badged_strategy,
    run_instructor_training_completed_not_badged_strategy,
)
from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from emails.signals import INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME
from workshops.models import (
    Badge,
    Event,
    Organization,
    Person,
    Role,
    Tag,
    Task,
    TrainingProgress,
    TrainingRequirement,
)
from workshops.tests.base import TestBase


class TestInstructorTrainingCompletedNotBadgedReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
            end=date.today() + timedelta(days=31),
        )
        ttt_tag = Tag.objects.get(name="TTT")
        event.tags.add(ttt_tag)

        learner = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            bluesky="@purdy_kelsi.bsky.social",
            mastodon="https://mastodon.social/@sdfgh",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        learner_role = Role.objects.get(name="learner")
        Task.objects.create(event=event, person=learner, role=learner_role)

        training_requirement = TrainingRequirement.objects.get(name="Training")

        url = reverse("trainingprogress_add")
        payload = {
            "trainee": learner.pk,
            "requirement": training_requirement.pk,
            "event": event.pk,
            "state": "p",
            "trainee_notes": "",
        }

        # Act
        rv = self.client.post(url, data=payload)

        # Arrange
        self.assertEqual(rv.status_code, 302)
        ScheduledEmail.objects.get(template=template)


class TestInstructorTrainingCompletedNotBadgedUpdateReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        signal = INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
            end=date.today() + timedelta(days=31),
        )
        ttt_tag = Tag.objects.get(name="TTT")
        event.tags.add(ttt_tag)

        learner = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            bluesky="@purdy_kelsi.bsky.social",
            mastodon="",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        learner_role = Role.objects.get(name="learner")
        Task.objects.create(event=event, person=learner, role=learner_role)
        request = RequestFactory().get("/")

        training_requirement = TrainingRequirement.objects.get(name="Training")
        demo_requirement = TrainingRequirement.objects.get(name="Demo")

        TrainingProgress.objects.create(
            trainee=learner,
            requirement=training_requirement,
            event=event,
            state="p",
        )

        with patch("emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_instructor_training_completed_not_badged_strategy(
                instructor_training_completed_not_badged_strategy(learner),
                request=request,
                person=learner,
                training_completed_date=event.end,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("trainingprogress_add")
        payload = {
            "trainee": learner.pk,
            "requirement": demo_requirement.pk,
            "state": "p",
            "trainee_notes": "",
        }

        # Act
        rv = self.client.post(url, payload)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, f"Updated {signal}")


class TestInstructorTrainingCompletedNotBadgedCancelIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        signal = INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
            end=date.today() + timedelta(days=31),
        )
        ttt_tag = Tag.objects.get(name="TTT")
        event.tags.add(ttt_tag)

        learner = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            bluesky="@purdy_kelsi.bsky.social",
            mastodon="",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        learner_role = Role.objects.get(name="learner")
        Task.objects.create(event=event, person=learner, role=learner_role)
        request = RequestFactory().get("/")

        training_requirement = TrainingRequirement.objects.get(name="Training")
        get_involved_requirement = TrainingRequirement.objects.get(name="Get Involved")
        welcome_requirement = TrainingRequirement.objects.get(name="Welcome Session")
        demo_requirement = TrainingRequirement.objects.get(name="Demo")

        TrainingProgress.objects.bulk_create(
            [
                TrainingProgress(
                    trainee=learner,
                    requirement=training_requirement,
                    event=event,
                    state="p",
                ),
                TrainingProgress(
                    trainee=learner,
                    requirement=get_involved_requirement,
                    state="p",
                ),
                TrainingProgress(
                    trainee=learner,
                    requirement=welcome_requirement,
                    state="p",
                ),
            ]
        )

        with patch("emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_instructor_training_completed_not_badged_strategy(
                instructor_training_completed_not_badged_strategy(learner),
                request=request,
                person=learner,
                training_completed_date=event.end,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("trainingprogress_add")
        payload = {
            "trainee": learner.pk,
            "requirement": demo_requirement.pk,
            "state": "p",
            "trainee_notes": "",
        }

        # Act
        rv = self.client.post(url, payload)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, "Email was cancelled")

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration_badge_awarded(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        signal = INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        ttt_organization = Organization.objects.create(domain="carpentries.org", fullname="Instructor Training")
        event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
            end=date.today() + timedelta(days=31),
        )
        ttt_tag = Tag.objects.get(name="TTT")
        event.tags.add(ttt_tag)

        learner = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            bluesky="@purdy_kelsi.bsky.social",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        learner_role = Role.objects.get(name="learner")
        Task.objects.create(event=event, person=learner, role=learner_role)
        request = RequestFactory().get("/")

        instructor_badge, _ = Badge.objects.get_or_create(name="instructor")

        training_requirement = TrainingRequirement.objects.get(name="Training")
        get_involved_requirement = TrainingRequirement.objects.get(name="Get Involved")
        welcome_requirement = TrainingRequirement.objects.get(name="Welcome Session")

        TrainingProgress.objects.bulk_create(
            [
                TrainingProgress(
                    trainee=learner,
                    requirement=training_requirement,
                    event=event,
                    state="p",
                ),
                TrainingProgress(
                    trainee=learner,
                    requirement=get_involved_requirement,
                    state="p",
                ),
                TrainingProgress(
                    trainee=learner,
                    requirement=welcome_requirement,
                    state="p",
                ),
            ]
        )

        with patch("emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_instructor_training_completed_not_badged_strategy(
                instructor_training_completed_not_badged_strategy(learner),
                request=request,
                person=learner,
                training_completed_date=event.end,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("award_add")
        payload = {
            "award-person": learner.pk,
            "award-badge": instructor_badge.pk,
            "award-awarded": "2025-05-06",
        }

        # Act
        rv = self.client.post(url, payload)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("-created_at").first()
        assert latest_log
        self.assertEqual(latest_log.details, "Email was cancelled")
