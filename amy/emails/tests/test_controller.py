from django.test import TestCase
from django.utils import timezone

from emails.controller import EmailController
from emails.models import EmailTemplate, ScheduledEmailLog


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
            context={"name": "James"},
            scheduled_at=now,
            to_header=["harry@potter.com"],
        )
        log = ScheduledEmailLog.objects.get(scheduled_email__pk=scheduled_email.pk)

        # Assert
        self.assertEqual(template, scheduled_email.template)
        self.assertEqual(scheduled_email.subject, "Greetings James")
        self.assertEqual(scheduled_email.body, "Hello, James! Nice to meet **you**.")
        self.assertEqual(scheduled_email.scheduled_at, now)
        self.assertEqual(log.scheduled_email, scheduled_email)
        self.assertEqual(log.details, f"Scheduled {signal} to run at {now.isoformat()}")
