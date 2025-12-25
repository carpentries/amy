import base64
from datetime import datetime
from functools import partial
from uuid import uuid4

from django.db.models import Model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from src.emails.controller import EmailController
from src.emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from src.emails.schemas import ContextModel, ToHeaderModel
from src.emails.utils import api_model_url, scalar_value_url
from src.workshops.models import Person
from src.workshops.tests.base import SuperuserMixin


def basic_auth_header(username: str, password: str) -> str:
    encoded = base64.b64encode((f"{username}:{password}").encode("ascii")).decode()
    return f"Basic {encoded}"


def token_auth_header(token: str) -> str:
    return f"Token {token}"


class TestScheduledEmailsAPI(SuperuserMixin, TestCase):
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
        self._setUpSuperuser()
        self._superUserConsent()
        self.urls = {
            "token": reverse("knox_login"),
            "scheduled_to_run": reverse("api-v2:scheduledemail-scheduled-to-run"),
            "lock": partial(reverse, "api-v2:scheduledemail-lock"),
            "fail": partial(reverse, "api-v2:scheduledemail-fail"),
            "succeed": partial(reverse, "api-v2:scheduledemail-succeed"),
        }

    def create_scheduled_email(
        self,
        scheduled_at: datetime,
        generic_relation_obj: Model | None = None,
        author: Person | None = None,
    ) -> ScheduledEmail:
        return EmailController.schedule_email(
            self.signal,
            context_json=ContextModel({"name": scalar_value_url("str", "Harry")}),
            scheduled_at=scheduled_at,
            to_header=["harry@potter.com"],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.harry.pk),
                        "property": "email",
                    }  # type: ignore
                ]
            ),
            generic_relation_obj=generic_relation_obj,
            author=author,
        )

    def get_auth_token(self) -> str:
        response = self.client.post(
            self.urls["token"],
            HTTP_AUTHORIZATION=basic_auth_header(self.admin.username, self.admin_password),
        )
        return response.json()["token"]

    def test_scheduled_to_run(self) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        token = self.get_auth_token()

        # Act
        response = self.client.get(
            self.urls["scheduled_to_run"],
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        results = response.json()["results"]
        self.assertEqual(results[0]["pk"], str(scheduled_email.pk))

    def test_scheduled_to_run__invalid_token_returns_401(self) -> None:
        # Act
        response = self.client.get(
            self.urls["scheduled_to_run"],
            HTTP_AUTHORIZATION=token_auth_header("invalid_token"),
        )

        # Assert
        self.assertEqual(response.status_code, 401)

    def test_scheduled_to_run__unauthorized_returns_401(self) -> None:
        # Act
        response = self.client.get(self.urls["scheduled_to_run"])

        # Assert
        self.assertEqual(response.status_code, 401)

    def test_lock(self) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        token = self.get_auth_token()

        # Act
        response = self.client.post(
            self.urls["lock"](args=[scheduled_email.pk]),
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["pk"], str(scheduled_email.pk))
        self.assertEqual(result["state"], ScheduledEmailStatus.LOCKED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).latest("created_at")
        self.assertEqual(latest_log.details, "State changed by worker")
        self.assertEqual(latest_log.state_before, ScheduledEmailStatus.SCHEDULED)
        self.assertEqual(latest_log.state_after, ScheduledEmailStatus.LOCKED)

    def test_lock__nonexisting_email_returns_404(self) -> None:
        # Arrange
        token = self.get_auth_token()

        # Act
        response = self.client.post(
            self.urls["lock"](args=[str(uuid4())]),
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 404)

    def test_lock__invalid_token_returns_401(self) -> None:
        # Act
        response = self.client.post(
            self.urls["lock"](args=[str(uuid4())]),
            HTTP_AUTHORIZATION=token_auth_header("invalid_token"),
        )

        # Assert
        self.assertEqual(response.status_code, 401)

    def test_lock__unauthorized_returns_401(self) -> None:
        # Act
        response = self.client.post(self.urls["lock"](args=[str(uuid4())]))

        # Assert
        self.assertEqual(response.status_code, 401)

    def test_fail(self) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        token = self.get_auth_token()
        details = "State changed by tests"

        # Act
        response = self.client.post(
            self.urls["fail"](args=[scheduled_email.pk]),
            {"details": details},
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["pk"], str(scheduled_email.pk))
        self.assertEqual(result["state"], ScheduledEmailStatus.FAILED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).latest("created_at")
        self.assertEqual(latest_log.details, details)
        self.assertEqual(latest_log.state_before, ScheduledEmailStatus.SCHEDULED)
        self.assertEqual(latest_log.state_after, ScheduledEmailStatus.FAILED)

    def test_fail__invalid_payload_returns_400(self) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        token = self.get_auth_token()

        # Act
        response = self.client.post(
            self.urls["fail"](args=[scheduled_email.pk]),
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 400)

    def test_fail__nonexisting_email_returns_404(self) -> None:
        # Arrange
        token = self.get_auth_token()

        # Act
        response = self.client.post(
            self.urls["fail"](args=[str(uuid4())]),
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 404)

    def test_fail__invalid_token_returns_401(self) -> None:
        # Act
        response = self.client.post(
            self.urls["fail"](args=[str(uuid4())]),
            HTTP_AUTHORIZATION=token_auth_header("invalid_token"),
        )

        # Assert
        self.assertEqual(response.status_code, 401)

    def test_fail__unauthorized_returns_401(self) -> None:
        # Act
        response = self.client.post(self.urls["fail"](args=[str(uuid4())]))

        # Assert
        self.assertEqual(response.status_code, 401)

    def test_succeed(self) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        token = self.get_auth_token()
        details = "State changed by tests"

        # Act
        response = self.client.post(
            self.urls["succeed"](args=[scheduled_email.pk]),
            {"details": details},
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["pk"], str(scheduled_email.pk))
        self.assertEqual(result["state"], ScheduledEmailStatus.SUCCEEDED)
        latest_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).latest("created_at")
        self.assertEqual(latest_log.details, details)
        self.assertEqual(latest_log.state_before, ScheduledEmailStatus.SCHEDULED)
        self.assertEqual(latest_log.state_after, ScheduledEmailStatus.SUCCEEDED)

    def test_succeed__invalid_payload_returns_400(self) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        token = self.get_auth_token()

        # Act
        response = self.client.post(
            self.urls["succeed"](args=[scheduled_email.pk]),
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 400)

    def test_succeed__nonexisting_email_returns_404(self) -> None:
        # Arrange
        token = self.get_auth_token()

        # Act
        response = self.client.post(
            self.urls["succeed"](args=[str(uuid4())]),
            HTTP_AUTHORIZATION=token_auth_header(token),
        )

        # Assert
        self.assertEqual(response.status_code, 404)

    def test_succeed__invalid_token_returns_401(self) -> None:
        # Act
        response = self.client.post(
            self.urls["succeed"](args=[str(uuid4())]),
            HTTP_AUTHORIZATION=token_auth_header("invalid_token"),
        )

        # Assert
        self.assertEqual(response.status_code, 401)

    def test_succeed__unauthorized_returns_401(self) -> None:
        # Act
        response = self.client.post(self.urls["succeed"](args=[str(uuid4())]))

        # Assert
        self.assertEqual(response.status_code, 401)
