from datetime import UTC, datetime, timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
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


class TestEmailTemplateDetailView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        url = reverse("email_template_detail", kwargs={"pk": template.pk})

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(rv.context["email_template"], template)
        self.assertEqual(rv.context["title"], f'Email template "{template}"')
        self.assertEqual(
            rv.context["rendered_body"],
            "<p>Hello, {{ name }}! Nice to meet <strong>you</strong>.</p>",
        )


class TestEmailTemplateCreateView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        url = reverse("email_template_create")
        data = {
            "name": "Greetings",
            "signal": "greetings",
            "from_header": "noreply@carpentries.org",
            "reply_to_header": "",
            "cc_header": "",
            "bcc_header": "",
            "subject": "Welcome, Hermione",
            "body": "Hi Hermione!",
        }

        # Act
        rv = self.client.post(url, data)

        # Assert
        self.assertEqual(rv.status_code, 302)
        template = EmailTemplate.objects.get(name="Greetings")

        self.assertEqual(template.signal, "greetings")
        self.assertEqual(template.from_header, "noreply@carpentries.org")
        self.assertEqual(template.reply_to_header, "")
        self.assertEqual(template.cc_header, [])
        self.assertEqual(template.bcc_header, [])
        self.assertEqual(template.subject, "Welcome, Hermione")
        self.assertEqual(template.body, "Hi Hermione!")


class TestEmailTemplateUpdateView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        url = reverse("email_template_edit", kwargs={"pk": template.pk})
        data = {
            "name": "Greetings",
            "signal": "greetings",
            "from_header": "noreply@carpentries.org",
            "reply_to_header": "",
            "cc_header": "",
            "bcc_header": "",
            "subject": "Welcome, Hermione",
            "body": "Hi Hermione!",
        }

        # Act
        rv = self.client.post(url, data)

        # Assert
        self.assertEqual(rv.status_code, 302)
        template.refresh_from_db()

        self.assertEqual(template.name, "Greetings")
        self.assertEqual(template.signal, "greetings")
        self.assertEqual(template.from_header, "noreply@carpentries.org")
        self.assertEqual(template.reply_to_header, "")
        self.assertEqual(template.cc_header, [])
        self.assertEqual(template.bcc_header, [])
        self.assertEqual(template.subject, "Welcome, Hermione")
        self.assertEqual(template.body, "Hi Hermione!")


class TestEmailTemplateDeleteView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        url = reverse("email_template_delete", kwargs={"pk": template.pk})

        # Act
        rv = self.client.post(url)

        # Assert
        self.assertEqual(rv.status_code, 302)
        with self.assertRaises(EmailTemplate.DoesNotExist):
            template.refresh_from_db()


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


class TestScheduledEmailDetailView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Harry"}
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net"],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.render_template(engine, template.subject, context),
            body=template.render_template(engine, template.body, context),
            template=template,
        )
        url = reverse("scheduled_email_detail", kwargs={"pk": scheduled_email.pk})

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(
            rv.context["scheduled_email"],
            scheduled_email,
        )
        self.assertEqual(
            rv.context["title"], f'Scheduled email "{scheduled_email.subject}"'
        )
        self.assertEqual(
            list(rv.context["log_entries"]),
            list(
                ScheduledEmailLog.objects.filter(
                    scheduled_email=scheduled_email
                ).order_by("-created_at")
            ),
        )
        self.assertEqual(
            rv.context["rendered_body"],
            "<p>Hello, Harry! Nice to meet <strong>you</strong>.</p>",
        )


class TestScheduledEmailUpdateView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Harry"}
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net"],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.render_template(engine, template.subject, context),
            body=template.render_template(engine, template.body, context),
            template=template,
        )
        url = reverse("scheduled_email_edit", kwargs={"pk": scheduled_email.pk})
        data = {
            "to_header": "hermione@granger.com",
            "from_header": "noreply@carpentries.org",
            "reply_to_header": "",
            "cc_header": "",
            "bcc_header": "",
            "subject": "Welcome, Hermione",
            "body": "Hi Hermione!",
        }

        # Act
        rv = self.client.post(url, data)

        # Assert
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        email_log = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).order_by("-created_at")[0]

        self.assertEqual(scheduled_email.to_header, ["hermione@granger.com"])
        self.assertEqual(scheduled_email.from_header, "noreply@carpentries.org")
        self.assertEqual(scheduled_email.reply_to_header, "")
        self.assertEqual(scheduled_email.cc_header, [])
        self.assertEqual(scheduled_email.bcc_header, [])
        self.assertEqual(scheduled_email.subject, "Welcome, Hermione")
        self.assertEqual(scheduled_email.body, "Hi Hermione!")

        self.assertEqual(email_log.details, "Scheduled email was changed.")
        self.assertEqual(email_log.state_before, email_log.state_after)
        self.assertEqual(email_log.state_after, ScheduledEmailStatus.SCHEDULED)


class TestScheduledEmailRescheduleView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Harry"}
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net"],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.render_template(engine, template.subject, context),
            body=template.render_template(engine, template.body, context),
            template=template,
        )
        url = reverse("scheduled_email_reschedule", kwargs={"pk": scheduled_email.pk})
        new_scheduled_date = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)
        data = {
            "scheduled_at_0": f"{new_scheduled_date:%Y-%m-%d}",
            "scheduled_at_1": f"{new_scheduled_date:%H:%M:%S}",
        }

        # Act
        rv = self.client.post(url, data)

        # Assert
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.scheduled_at, new_scheduled_date)


class TestScheduledEmailCancelView(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="test_email_template1",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Harry"}
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net"],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.render_template(engine, template.subject, context),
            body=template.render_template(engine, template.body, context),
            template=template,
        )
        url = reverse("scheduled_email_cancel", kwargs={"pk": scheduled_email.pk})

        # Act
        rv = self.client.post(url, {"confirm": "yes"})

        # Assert
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
