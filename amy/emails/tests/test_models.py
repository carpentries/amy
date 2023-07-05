from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)


class TestEmailTemplate(TestCase):
    def test_get_engine__default(self) -> None:
        # Arrange
        expected_engine_name = settings.EMAIL_TEMPLATE_ENGINE_BACKEND
        # Act
        result = EmailTemplate.get_engine()
        # Assert
        self.assertEqual(EmailTemplate.get_engine(expected_engine_name), result)

    def test_render_template(self) -> None:
        # Arrange
        template = "Hello, {{ name }}{% if lastname %} {{ lastname }}{% endif %}."
        context = {
            "name": "James",
            "lastname": "Bond",
        }
        expected = "Hello, James Bond."
        engine = EmailTemplate.get_engine()

        # Act
        result = EmailTemplate.render_template(engine, template, context)

        # Assert
        self.assertEqual(result, expected)

    def test_validate_template__correct(self) -> None:
        # Arrange
        template = "Hello, {{ name }}{% if lastname %} {{ lastname }}{% endif %}."
        context = {
            "name": "James",
            "lastname": "Bond",
        }
        engine = EmailTemplate.get_engine()

        # Act
        result = EmailTemplate().validate_template(engine, template, context)

        # Assert
        self.assertTrue(result)

    def test_validate_template__invalid(self) -> None:
        # Arrange
        template = "Hello, {{ names }{% if lastname } {{ lastname }}."
        context = {
            "name": "James",
            "lastname": "Bond",
        }
        engine = EmailTemplate.get_engine()

        # Act & Assert
        with self.assertRaises(ValidationError):
            EmailTemplate().validate_template(engine, template, context)

    def test_clean__subject_invalid(self) -> None:
        # Arrange
        template = EmailTemplate(
            name="test-email",
            signal="test-email",
            subject="Hello world! {% if value %} no endif",
            body="",
        )
        # Act
        with self.assertRaises(ValidationError) as ctx:
            template.clean()
        # Assert
        self.assertEqual(ctx.exception.error_dict.keys(), {"subject"})

    def test_clean__body_invalid(self) -> None:
        # Arrange
        template = EmailTemplate(
            name="test-email",
            signal="test-email",
            subject="",
            body="Hello world! {% if value %} no endif",
        )
        # Act
        with self.assertRaises(ValidationError) as ctx:
            template.clean()
        # Assert
        self.assertEqual(ctx.exception.error_dict.keys(), {"body"})

    def test_clean(self) -> None:
        # Arrange
        template = EmailTemplate(
            name="test-email",
            signal="test-email",
            subject="Hello World!",
            body="Hi **Everyone**!",
        )
        # Act
        result = template.clean()
        # Assert
        self.assertIsNone(result)

    def test_object_create(self) -> None:
        # Act
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal="test_email_template",
            from_header="workshops@carpentries.org",
            # Intentionally omitted.
            # reply_to_header="",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        # Assert
        self.assertIsNotNone(template.id)  # `id` should be UUID
        self.assertEqual(str(template), "Test Email Template")

    def test_get_absolute_url(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal="test_email_template",
            subject="Greetings {{ name }}",
            from_header="workshops@carpentries.org",
            # Intentionally omitted.
            # reply_to_header="",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        # Act
        url = template.get_absolute_url()

        # Assert
        self.assertEqual(
            url, reverse("email_template_detail", kwargs={"pk": template.pk})
        )


class TestScheduledEmail(TestCase):
    def test_object_create(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal="test_email_template",
            subject="Greetings {{ name }}",
            from_header="workshops@carpentries.org",
            # Intentionally omitted.
            # reply_to_header="",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Tony Stark"}
        # Act
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net", "harry@potter.co.uk"],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.render_template(engine, template.subject, context),
            body=template.render_template(engine, template.body, context),
            template=template,
        )
        # Assert
        self.assertIsNotNone(scheduled_email.id)  # `id` should be UUID
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        self.assertEqual(
            scheduled_email.body, "Hello, Tony Stark! Nice to meet **you**."
        )
        self.assertEqual(
            str(scheduled_email),
            "['peter@spiderman.net', 'harry@potter.co.uk']: Greetings Tony Stark",
        )

    def test_get_absolute_url(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal="test_email_template",
            subject="Greetings {{ name }}",
            from_header="workshops@carpentries.org",
            # Intentionally omitted.
            # reply_to_header="",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Tony Stark"}
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net", "harry@potter.co.uk"],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.render_template(engine, template.subject, context),
            body=template.render_template(engine, template.body, context),
            template=template,
        )
        # Act
        url = scheduled_email.get_absolute_url()

        # Assert
        self.assertEqual(
            url, reverse("scheduled_email_detail", kwargs={"pk": scheduled_email.pk})
        )


class TestScheduledEmailLog(TestCase):
    def test_object_create(self) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal="test_email_template",
            subject="Greetings {{ name }}",
            from_header="workshops@carpentries.org",
            # Intentionally omitted.
            # reply_to_header="",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        engine = EmailTemplate.get_engine()
        context = {"name": "Tony Stark"}
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net", "harry@potter.co.uk"],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.render_template(engine, template.subject, context),
            body=template.render_template(engine, template.body, context),
            template=template,
        )
        # Act
        log = ScheduledEmailLog.objects.create(
            details="Preparing scheduled email",
            state_after=ScheduledEmailStatus.SCHEDULED,
            scheduled_email=scheduled_email,
        )
        # Assert
        self.assertIsNotNone(log.id)  # `id` should be UUID
        self.assertIsNone(log.state_before)
        self.assertEqual(str(log), "[None->scheduled]: Preparing scheduled email")
