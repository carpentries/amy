from datetime import UTC, datetime, timedelta

from django.template.exceptions import TemplateSyntaxError
from django.test import TestCase
from django.utils import timezone

from emails.controller import EmailController, EmailControllerException
from emails.models import EmailTemplate, ScheduledEmailLog, ScheduledEmailStatus
from emails.schemas import ContextModel, ToHeaderModel
from emails.utils import api_model_url, scalar_value_url
from workshops.models import Person


class TestEmailController(TestCase):
    def setUp(self) -> None:
        self.harry = Person.objects.create(
            personal="Harry",
            family="Potter",
            email="harry@potter.com",
            username="potter_harry",
        )
        self.signal = "test_email_template"
        self.template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=self.signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    def test_schedule_email(self) -> None:
        # Arrange
        now = timezone.now()

        # Act
        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=now,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
        )
        log = ScheduledEmailLog.objects.get(scheduled_email__pk=scheduled_email.pk)

        # Assert
        self.assertEqual(self.template, scheduled_email.template)
        self.assertEqual(scheduled_email.subject, "Greetings {{ name }}")
        self.assertEqual(scheduled_email.context_json, {"name": "value:str#Harry"})
        self.assertEqual(
            scheduled_email.body, "Hello, {{ name }}! Nice to meet **you**."
        )
        self.assertEqual(scheduled_email.scheduled_at, now)
        self.assertEqual(scheduled_email.to_header, ["harry@potter.com"])
        self.assertEqual(
            scheduled_email.to_header_context_json,
            [{"api_uri": f"api:person#{self.harry.pk}", "property": "email"}],
        )
        self.assertEqual(log.scheduled_email, scheduled_email)
        self.assertEqual(
            log.details, f"Scheduled {self.signal} to run at {now.isoformat()}"
        )

    def test_schedule_email__no_recipients(self) -> None:
        # Arrange
        now = timezone.now()
        signal = "test_email_template"

        # Act & Assert
        with self.assertRaisesMessage(
            EmailControllerException,
            "Email must have at least one recipient, but `to_header` or "
            "`to_header_context_json` are empty.",
        ):
            EmailController.schedule_email(
                signal,
                context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
                scheduled_at=now,
                to_header=[],
                to_header_context_json=ToHeaderModel([]),
            )

    def test_schedule_email__no_template(self) -> None:
        # Arrange
        now = timezone.now()
        self.template.delete()

        # Act & Assert
        with self.assertRaises(EmailTemplate.DoesNotExist):
            EmailController.schedule_email(
                self.signal,
                context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
                scheduled_at=now,
                to_header=["harry@potter.com"],
                to_header_context_json=ToHeaderModel(
                    [
                        {
                            "api_uri": api_model_url("person", self.harry.pk),
                            "property": "email",
                        }
                    ]  # type: ignore
                ),
            )

    def test_schedule_email__inactive_template(self) -> None:
        # Arrange
        now = timezone.now()
        self.template.active = False
        self.template.save()

        # Act & Assert
        with self.assertRaises(EmailTemplate.DoesNotExist):
            EmailController.schedule_email(
                self.signal,
                context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
                scheduled_at=now,
                to_header=["harry@potter.com"],
                to_header_context_json=ToHeaderModel(
                    [
                        {
                            "api_uri": api_model_url("person", self.harry.pk),
                            "property": "email",
                        }
                    ]  # type: ignore
                ),
            )

    def test_schedule_email__invalid_template(self) -> None:
        # Arrange
        now = timezone.now()
        self.template.subject = "Greetings {% if name %}{{ name }}"
        self.template.save()

        # Act & Assert
        with self.assertRaises(TemplateSyntaxError):
            EmailController.schedule_email(
                self.signal,
                context_json=ContextModel({"name": scalar_value_url("str", "James")}),
                scheduled_at=now,
                to_header=["harry@potter.com"],
                to_header_context_json=ToHeaderModel(
                    [
                        {
                            "api_uri": api_model_url("person", self.harry.pk),
                            "property": "email",
                        }
                    ]  # type: ignore
                ),
            )

    def test_schedule_email__generic_object_link(self) -> None:
        # Arrange
        now = timezone.now()
        person = Person(personal="Harry", family="Potter")

        # Act
        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=now,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
            generic_relation_obj=person,
        )

        # Assert
        self.assertEqual(scheduled_email.generic_relation, person)

    def test_schedule_email__author(self) -> None:
        # Arrange
        now = timezone.now()

        # Act
        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=now,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
            author=self.harry,
        )
        log = ScheduledEmailLog.objects.get(scheduled_email=scheduled_email)

        # Assert
        self.assertEqual(log.author, self.harry)

    def test_reschedule_email(self) -> None:
        # Arrange
        old_scheduled_date = datetime(2023, 7, 5, 10, 00, tzinfo=UTC)
        new_scheduled_date = datetime(2024, 7, 5, 10, 00, tzinfo=UTC)

        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=old_scheduled_date,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
        )

        # Act
        logs_count = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).count()
        scheduled_email = EmailController.reschedule_email(
            scheduled_email,
            new_scheduled_date,
            author=self.harry,
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
        self.assertEqual(latest_log.author, self.harry)

    def test_reschedule_cancelled_email(self) -> None:
        # Arrange
        old_scheduled_date = datetime(2023, 7, 5, 10, 00, tzinfo=UTC)
        new_scheduled_date = datetime(2024, 7, 5, 10, 00, tzinfo=UTC)

        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=old_scheduled_date,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
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

        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=now,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
        )

        # Act
        logs_count = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).count()
        scheduled_email = EmailController.cancel_email(
            scheduled_email,
            author=self.harry,
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
        self.assertEqual(latest_log.author, self.harry)

    def test_update_scheduled_email(self) -> None:
        # Arrange
        now = timezone.now()

        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=now,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
        )

        # Act
        logs_count = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).count()
        scheduled_email = EmailController.update_scheduled_email(
            scheduled_email,
            context_json=ContextModel({"name": scalar_value_url("str", "James")}),
            scheduled_at=now + timedelta(hours=1),
            to_header=["james@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "secondary_email",
                    }
                ]  # type: ignore
            ),
            generic_relation_obj=None,
            author=self.harry,
        )

        # Assert
        self.assertEqual(self.template, scheduled_email.template)
        self.assertEqual(scheduled_email.subject, "Greetings {{ name }}")
        self.assertEqual(scheduled_email.context_json, {"name": "value:str#James"})
        self.assertEqual(
            scheduled_email.body, "Hello, {{ name }}! Nice to meet **you**."
        )
        self.assertEqual(scheduled_email.scheduled_at, now + timedelta(hours=1))
        self.assertEqual(scheduled_email.to_header, ["james@potter.com"])
        self.assertEqual(
            scheduled_email.to_header_context_json,
            [{"api_uri": f"api:person#{self.harry.pk}", "property": "secondary_email"}],
        )

        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        self.assertEqual(
            ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).count(),
            logs_count + 1,
        )
        latest_log = ScheduledEmailLog.objects.filter(
            scheduled_email=scheduled_email
        ).order_by("-created_at")[0]
        self.assertEqual(latest_log.details, f"Updated {self.signal}")
        self.assertEqual(latest_log.author, self.harry)

    def test_update_scheduled_email__no_recipients(self) -> None:
        # Arrange
        now = timezone.now()

        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=now,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
        )

        # Act & Assert
        with self.assertRaisesMessage(
            EmailControllerException,
            "Email must have at least one recipient, but `to_header` or "
            "`to_header_context_json` are empty.",
        ):
            EmailController.update_scheduled_email(
                scheduled_email,
                context_json=ContextModel({"name": scalar_value_url("str", "James")}),
                scheduled_at=now + timedelta(hours=1),
                to_header=[],
                to_header_context_json=ToHeaderModel([]),
                generic_relation_obj=None,
                author=self.harry,
            )

    def test_update_scheduled_email__missing_template(self) -> None:
        # Arrange
        now = timezone.now()

        scheduled_email = EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=now,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }
                ]  # type: ignore
            ),
        )

        # Shouldn't occur in real life, but let's test it anyway.
        scheduled_email.template = None
        scheduled_email.save()

        # Act & Assert
        with self.assertRaisesMessage(
            EmailControllerException,
            "Scheduled email must be linked to a template.",
        ):
            EmailController.update_scheduled_email(
                scheduled_email,
                context_json=ContextModel({"name": scalar_value_url("str", "James")}),
                scheduled_at=now + timedelta(hours=1),
                to_header=["james@potter.com"],
                to_header_context_json=ToHeaderModel(
                    [
                        {
                            "api_uri": api_model_url("person", self.harry.pk),
                            "property": "secondary_email",
                        }
                    ]  # type: ignore
                ),
                generic_relation_obj=None,
                author=self.harry,
            )
