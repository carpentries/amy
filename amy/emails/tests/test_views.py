from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from emails.models import EmailTemplate, ScheduledEmail
from workshops.tests.base import TestBase


class TestEmailTemplateListView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template1 = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        template2 = EmailTemplate.objects.create(
            name="Test Email Template2",
            signal="test_email_template2",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        url = reverse("email_templates_list")

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(list(rv.context["email_templates"]), [template1, template2])
        self.assertEqual(rv.context["title"], "Email templates")


class TestScheduledEmailListView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template1 = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        template2 = EmailTemplate.objects.create(
            name="Test Email Template2",
            signal="test_email_template2",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Harry"}
        scheduled_email1 = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net"],
            from_header=template1.from_header,
            reply_to_header=template1.reply_to_header,
            cc_header=template1.cc_header,
            bcc_header=template1.bcc_header,
            subject=template1.render_template(engine, template1.subject, context),
            body=template1.render_template(engine, template1.body, context),
            template=template1,
        )
        scheduled_email2 = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=3),
            to_header=["harry@potter.co.uk"],
            from_header=template2.from_header,
            reply_to_header=template2.reply_to_header,
            cc_header=template2.cc_header,
            bcc_header=template2.bcc_header,
            subject=template2.render_template(engine, template2.subject, context),
            body=template2.render_template(engine, template2.body, context),
            template=template2,
        )
        url = reverse("scheduled_emails_list")

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(
            list(rv.context["scheduled_emails"]),
            [scheduled_email2, scheduled_email1],  # Due to ordering
        )
        self.assertEqual(rv.context["title"], "Scheduled emails")
