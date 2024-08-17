from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
    ScheduledEmailStatusActions,
    ScheduledEmailStatusExplanation,
)
from emails.types import PersonsMergedContext
from emails.views import (
    ScheduledEmailCancel,
    ScheduledEmailReschedule,
    ScheduledEmailUpdate,
)
from workshops.models import Person
from workshops.tests.base import TestBase


class TestAllEmailTemplates(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
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
        url = reverse("all_emailtemplates")

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(list(rv.context["email_templates"]), [template1, template2])
        self.assertEqual(rv.context["title"], "Email templates")


class TestEmailTemplateDetails(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="persons_merged",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        url = reverse("emailtemplate_details", kwargs={"pk": template.pk})

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(rv.context["email_template"], template)
        self.assertEqual(rv.context["title"], f'Email template "{template}"')
        self.assertEqual(
            rv.context["rendered_body"],
            "<p>Hello, {{ name }}! Nice to meet <strong>you</strong>.</p>",
        )
        self.assertEqual(rv.context["body_context_type"], PersonsMergedContext)
        self.assertEqual(
            rv.context["body_context_annotations"],
            {
                "person": repr(Person),
            },
        )


class TestEmailTemplateCreate(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        url = reverse("emailtemplate_add")
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
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_view_context(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="persons_merged",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        url = reverse("emailtemplate_edit", kwargs={"pk": template.pk})

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(
            rv.context["body_context_annotations"],
            {
                "person": repr(Person),
            },
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
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
        url = reverse("emailtemplate_edit", kwargs={"pk": template.pk})
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
        self.assertEqual(template.signal, "test_email_template1")
        self.assertEqual(template.from_header, "noreply@carpentries.org")
        self.assertEqual(template.reply_to_header, "")
        self.assertEqual(template.cc_header, [])
        self.assertEqual(template.bcc_header, [])
        self.assertEqual(template.subject, "Welcome, Hermione")
        self.assertEqual(template.body, "Hi Hermione!")


class TestEmailTemplateDeleteView(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
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
        url = reverse("emailtemplate_delete", kwargs={"pk": template.pk})

        # Act
        rv = self.client.post(url)

        # Assert
        self.assertEqual(rv.status_code, 302)
        with self.assertRaises(EmailTemplate.DoesNotExist):
            template.refresh_from_db()


class TestAllScheduledEmails(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
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
        url = reverse("all_scheduledemails")

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(
            list(rv.context["scheduled_emails"]),
            [scheduled_email2, scheduled_email1],  # Due to ordering
        )
        self.assertEqual(rv.context["title"], "Scheduled emails")


class TestScheduledEmailDetails(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_view(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="persons_merged",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ personal }} {{ family }}",
            body="Hello, {{ hermione.full_name }}! Nice to meet **you**. Here's a "
            "list of what you can do: {{ a_list }}.",
        )
        scheduled_email = ScheduledEmail.objects.create(
            scheduled_at=timezone.now() + timedelta(hours=1),
            to_header=["peter@spiderman.net"],
            to_header_context_json=[
                {"api_uri": f"api:person#{self.hermione.pk}", "property": "email"},
                {"value_uri": "value:str#test2@example.org"},
            ],
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=template.subject,
            body=template.body,
            context_json={
                "hermione": f"api:person#{self.hermione.pk}",
                "personal": "value:str#Harry",
                "family": "value:str#Potter",
                "a_list": ["value:int#1", "value:int#2"],
            },
            template=template,
        )
        url = reverse("scheduledemail_details", kwargs={"pk": scheduled_email.pk})

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
            rv.context["status_explanation"],
            ScheduledEmailStatusExplanation[
                ScheduledEmailStatus(scheduled_email.state)
            ],
        )
        self.assertEqual(
            rv.context["ScheduledEmailStatusActions"], ScheduledEmailStatusActions
        )
        self.assertEqual(
            rv.context["rendered_context"],
            {
                "a_list": [1, 2],
                "hermione": self.hermione,
                "personal": "Harry",
                "family": "Potter",
            },
        )
        self.assertEqual(
            rv.context["rendered_body"],
            "<p>Hello, Hermione Granger! Nice to meet <strong>you</strong>. "
            "Here's a list of what you can do: [1, 2].</p>",
        )
        self.assertEqual(rv.context["rendered_subject"], "Greetings Harry Potter")
        self.assertEqual(
            rv.context["rendered_to_header_context"],
            [self.hermione.email, "test2@example.org"],
        )


class TestScheduledEmailUpdate(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_view_context(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        template = EmailTemplate.objects.create(
            name="Test Email Template1",
            signal="persons_merged",
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
        url = reverse("scheduledemail_edit", kwargs={"pk": scheduled_email.pk})

        # Act
        rv = self.client.get(url)

        # Assert
        self.assertEqual(rv.status_code, 200)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
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
        url = reverse("scheduledemail_edit", kwargs={"pk": scheduled_email.pk})
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

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_allowed_email_statuses(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        view = ScheduledEmailUpdate(request=request)
        queryset = view.get_queryset()

        ScheduledEmail.objects.bulk_create(
            [
                ScheduledEmail(
                    scheduled_at=timezone.now() + timedelta(hours=1),
                    to_header=["peter@spiderman.net"],
                    from_header="test@example.org",
                    reply_to_header="",
                    cc_header=[],
                    bcc_header=[],
                    subject="Test",
                    body="Test",
                    state=state,
                )
                for state in [
                    ScheduledEmailStatus.SCHEDULED,
                    ScheduledEmailStatus.FAILED,
                ]
            ]
        )

        # Act
        results = queryset.all()

        # Assert - all of the defined scheduled emails can be retrieved with this query
        self.assertEqual(results.count(), 2)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_disallowed_email_statuses(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        view = ScheduledEmailUpdate(request=request)
        queryset = view.get_queryset()

        ScheduledEmail.objects.bulk_create(
            [
                ScheduledEmail(
                    scheduled_at=timezone.now() + timedelta(hours=1),
                    to_header=["peter@spiderman.net"],
                    from_header="test@example.org",
                    reply_to_header="",
                    cc_header=[],
                    bcc_header=[],
                    subject="Test",
                    body="Test",
                    state=state,
                )
                for state in [
                    ScheduledEmailStatus.LOCKED,
                    ScheduledEmailStatus.RUNNING,
                    ScheduledEmailStatus.CANCELLED,
                ]
            ]
        )

        # Act
        results = queryset.all()

        # Assert - none of the defined scheduled emails can be retrieved with this query
        self.assertEqual(results.count(), 0)


class TestScheduledEmailReschedule(TestBase):
    @patch("emails.forms.datetime", wraps=datetime)
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_view(self, mock_datetime: MagicMock) -> None:
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
        url = reverse("scheduledemail_reschedule", kwargs={"pk": scheduled_email.pk})
        mock_datetime.now.return_value = datetime(2022, 12, 31, 23, 59, 59, tzinfo=UTC)
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

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_allowed_email_statuses(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        view = ScheduledEmailReschedule(request=request)
        queryset = view.get_queryset()

        ScheduledEmail.objects.bulk_create(
            [
                ScheduledEmail(
                    scheduled_at=timezone.now() + timedelta(hours=1),
                    to_header=["peter@spiderman.net"],
                    from_header="test@example.org",
                    reply_to_header="",
                    cc_header=[],
                    bcc_header=[],
                    subject="Test",
                    body="Test",
                    state=state,
                )
                for state in [
                    ScheduledEmailStatus.SCHEDULED,
                    ScheduledEmailStatus.FAILED,
                    ScheduledEmailStatus.CANCELLED,
                ]
            ]
        )

        # Act
        results = queryset.all()

        # Assert - all of the defined scheduled emails can be retrieved with this query
        self.assertEqual(results.count(), 3)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_disallowed_email_statuses(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        view = ScheduledEmailReschedule(request=request)
        queryset = view.get_queryset()

        ScheduledEmail.objects.bulk_create(
            [
                ScheduledEmail(
                    scheduled_at=timezone.now() + timedelta(hours=1),
                    to_header=["peter@spiderman.net"],
                    from_header="test@example.org",
                    reply_to_header="",
                    cc_header=[],
                    bcc_header=[],
                    subject="Test",
                    body="Test",
                    state=state,
                )
                for state in [
                    ScheduledEmailStatus.LOCKED,
                    ScheduledEmailStatus.RUNNING,
                    ScheduledEmailStatus.SUCCEEDED,
                ]
            ]
        )

        # Act
        results = queryset.all()

        # Assert - none of the defined scheduled emails can be retrieved with this query
        self.assertEqual(results.count(), 0)


class TestScheduledEmailCancel(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
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
        url = reverse("scheduledemail_cancel", kwargs={"pk": scheduled_email.pk})

        # Act
        rv = self.client.post(url, {"confirm": "yes"})

        # Assert
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_allowed_email_statuses(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        view = ScheduledEmailCancel(request=request)
        queryset = view.get_queryset()

        ScheduledEmail.objects.bulk_create(
            [
                ScheduledEmail(
                    scheduled_at=timezone.now() + timedelta(hours=1),
                    to_header=["peter@spiderman.net"],
                    from_header="test@example.org",
                    reply_to_header="",
                    cc_header=[],
                    bcc_header=[],
                    subject="Test",
                    body="Test",
                    state=state,
                )
                for state in [
                    ScheduledEmailStatus.SCHEDULED,
                    ScheduledEmailStatus.FAILED,
                ]
            ]
        )

        # Act
        results = queryset.all()

        # Assert - all of the defined scheduled emails can be retrieved with this query
        self.assertEqual(results.count(), 2)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_disallowed_email_statuses(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        view = ScheduledEmailCancel(request=request)
        queryset = view.get_queryset()

        ScheduledEmail.objects.bulk_create(
            [
                ScheduledEmail(
                    scheduled_at=timezone.now() + timedelta(hours=1),
                    to_header=["peter@spiderman.net"],
                    from_header="test@example.org",
                    reply_to_header="",
                    cc_header=[],
                    bcc_header=[],
                    subject="Test",
                    body="Test",
                    state=state,
                )
                for state in [
                    ScheduledEmailStatus.LOCKED,
                    ScheduledEmailStatus.RUNNING,
                    ScheduledEmailStatus.SUCCEEDED,
                    ScheduledEmailStatus.CANCELLED,
                ]
            ]
        )

        # Act
        results = queryset.all()

        # Assert - none of the defined scheduled emails can be retrieved with this query
        self.assertEqual(results.count(), 0)
