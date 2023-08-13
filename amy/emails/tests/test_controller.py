from datetime import UTC, datetime

from django.template.exceptions import TemplateSyntaxError
from django.test import TestCase
from django.utils import timezone

from emails.controller import EmailController
from emails.models import EmailTemplate, ScheduledEmailLog, ScheduledEmailStatus
from workshops.models import Person


class TestEmailController(TestCase):
    def test_schedule_email(self) -> None:
        # Arrange
        now = timezone.now()
        signal = "test_email_template"
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        # Act
        scheduled_email = EmailController.schedule_email(
            signal,
            context={"name": "Harry"},
            scheduled_at=now,
            to_header=["harry@potter.com"],
        )
        log = ScheduledEmailLog.objects.get(scheduled_email__pk=scheduled_email.pk)

        # Assert
        self.assertEqual(template, scheduled_email.template)
        self.assertEqual(scheduled_email.subject, "Greetings Harry")
        self.assertEqual(scheduled_email.body, "Hello, Harry! Nice to meet **you**.")
        self.assertEqual(scheduled_email.scheduled_at, now)
        self.assertEqual(log.scheduled_email, scheduled_email)
        self.assertEqual(log.details, f"Scheduled {signal} to run at {now.isoformat()}")

    def test_schedule_email__no_template(self) -> None:
        # Arrange
        now = timezone.now()
        signal = "test_email_template"

        # Act & Assert
        with self.assertRaises(EmailTemplate.DoesNotExist):
            EmailController.schedule_email(
                signal,
                context={"name": "Harry"},
                scheduled_at=now,
                to_header=["harry@potter.com"],
            )

    def test_schedule_email__inactive_template(self) -> None:
        # Arrange
        now = timezone.now()
        signal = "test_email_template"
        EmailTemplate.objects.create(
            active=False,
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            # invalid Django template syntax
            subject="Greetings",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        # Act & Assert
        with self.assertRaises(EmailTemplate.DoesNotExist):
            EmailController.schedule_email(
                signal,
                context={"name": "Harry"},
                scheduled_at=now,
                to_header=["harry@potter.com"],
            )

    def test_schedule_email__invalid_template(self) -> None:
        # Arrange
        now = timezone.now()
        signal = "test_email_template"
        EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            # invalid Django template syntax
            subject="Greetings {% if name %}{{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        # Act & Assert
        with self.assertRaises(TemplateSyntaxError):
            EmailController.schedule_email(
                signal,
                context={"name": "James"},
                scheduled_at=now,
                to_header=["harry@potter.com"],
            )

    def test_schedule_email__generic_object_link(self) -> None:
        # Arrange
        now = timezone.now()
        signal = "test_email_template"
        person = Person(personal="Harry", family="Potter")
        EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        # Act
        scheduled_email = EmailController.schedule_email(
            signal,
            context={"name": "Harry"},
            scheduled_at=now,
            to_header=["harry@potter.com"],
            generic_relation_obj=person,
        )

        # Assert
        self.assertEqual(scheduled_email.generic_relation, person)

    def test_schedule_email__author(self) -> None:
        # Arrange
        now = timezone.now()
        person = Person.objects.create(personal="Harry", family="Potter")
        signal = "test_email_template"
        EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        # Act
        scheduled_email = EmailController.schedule_email(
            signal,
            context={"name": "Harry"},
            scheduled_at=now,
            to_header=["harry@potter.com"],
            author=person,
        )
        log = ScheduledEmailLog.objects.get(scheduled_email=scheduled_email)

        # Assert
        self.assertEqual(log.author, person)

    def test_reschedule_email(self) -> None:
        # Arrange
        old_scheduled_date = datetime(2023, 7, 5, 10, 00, tzinfo=UTC)
        new_scheduled_date = datetime(2024, 7, 5, 10, 00, tzinfo=UTC)
        person = Person.objects.create(personal="Harry", family="Potter")
        signal = "test_email_template"
        EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        scheduled_email = EmailController.schedule_email(
            signal,
            context={"name": "Harry"},
            scheduled_at=old_scheduled_date,
            to_header=["harry@potter.com"],
        )

        # Act
        logs_count = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).count()
        scheduled_email = EmailController.reschedule_email(
            scheduled_email,
            new_scheduled_date,
            author=person,
        )

        # Assert
        self.assertEqual(scheduled_email.scheduled_at, new_scheduled_date)
        self.assertEqual(
            ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).count(),
            logs_count + 1,
        )
        latest_log = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).order_by("-created_at")[0]
        self.assertEqual(
            latest_log.details,
            f"Rescheduled email to run at {new_scheduled_date.isoformat()}",
        )
        self.assertEqual(latest_log.author, person)

    def test_reschedule_cancelled_email(self) -> None:
        # Arrange
        old_scheduled_date = datetime(2023, 7, 5, 10, 00, tzinfo=UTC)
        new_scheduled_date = datetime(2024, 7, 5, 10, 00, tzinfo=UTC)
        signal = "test_email_template"
        EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        scheduled_email = EmailController.schedule_email(
            signal,
            context={"name": "Harry"},
            scheduled_at=old_scheduled_date,
            to_header=["harry@potter.com"],
        )
        cancelled_scheduled_email = EmailController.cancel_email(scheduled_email)

        # Act
        rescheduled_email = EmailController.reschedule_email(
            cancelled_scheduled_email,
            new_scheduled_date,
        )

        # Assert
        self.assertEqual(rescheduled_email.scheduled_at, new_scheduled_date)
        self.assertEqual(rescheduled_email.state, ScheduledEmailStatus.SCHEDULED)

    def test_cancel_email(self) -> None:
        # Arrange
        now = timezone.now()
        person = Person.objects.create(personal="Harry", family="Potter")
        signal = "test_email_template"
        EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

        scheduled_email = EmailController.schedule_email(
            signal,
            context={"name": "Harry"},
            scheduled_at=now,
            to_header=["harry@potter.com"],
        )

        # Act
        logs_count = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).count()
        scheduled_email = EmailController.cancel_email(
            scheduled_email,
            author=person,
        )

        # Assert
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
        self.assertEqual(
            ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).count(),
            logs_count + 1,
        )
        latest_log = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).order_by("-created_at")[0]
        self.assertEqual(latest_log.details, "Email was cancelled")
        self.assertEqual(latest_log.author, person)
