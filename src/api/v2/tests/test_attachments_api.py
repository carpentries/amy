from datetime import datetime
from functools import partial
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.db.models import Model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from src.emails.controller import EmailController
from src.emails.models import Attachment, EmailTemplate, ScheduledEmail
from src.emails.schemas import ContextModel, ToHeaderModel
from src.emails.utils import api_model_url, scalar_value_url
from src.workshops.models import Person
from src.workshops.tests.base import SuperuserMixin


class TestAttachmentsAPI(SuperuserMixin, TestCase):
    def setUp(self) -> None:
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
        self.url = partial(reverse, "api-v2:attachment-generate-presigned-url")

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
                        "api_uri": api_model_url("person", self.admin.pk),
                        "property": "email",
                    }  # type: ignore
                ]
            ),
            generic_relation_obj=generic_relation_obj,
            author=author,
        )

    def create_attachment(self, email: ScheduledEmail) -> Attachment:
        attachment = Attachment.objects.create(
            email=email,
            filename="certificate.pdf",
            s3_path="random/certificate.pdf",
            s3_bucket="random-bucket",
            presigned_url="",
            presigned_url_expiration=None,
        )
        return attachment

    def test_generate_presigned_url__invalid_id(self) -> None:
        # Arrange
        fake_id = uuid4()
        self._logSuperuserIn()

        # Act
        response = self.client.post(self.url(args=[fake_id]))

        # Assert
        self.assertEqual(response.status_code, 404)

    def test_generate_presigned_url__unauthorized(self) -> None:
        # Arrange
        fake_id = uuid4()

        # Act
        response = self.client.post(self.url(args=[fake_id]))

        # Assert
        self.assertEqual(response.status_code, 401)

    @patch("src.emails.controller.s3_client.generate_presigned_url")
    def test_generate_presigned_url__no_payload(self, mock_generate_presigned_url: MagicMock) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        attachment = self.create_attachment(scheduled_email)
        self._logSuperuserIn()
        mock_generate_presigned_url.return_value = "TestPresignedUrl"

        # Act
        response = self.client.post(self.url(args=[attachment.pk]))

        # Assert
        self.assertEqual(response.status_code, 200)

    def test_generate_presigned_url__invalid_payload(self) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        attachment = self.create_attachment(scheduled_email)
        self._logSuperuserIn()

        # Act
        response = self.client.post(
            self.url(args=[attachment.pk]),
            {
                "expiration_seconds": "invalid",
            },
        )

        # Assert
        self.assertEqual(response.status_code, 400)

    @patch("src.emails.controller.s3_client.generate_presigned_url")
    def test_generate_presigned_url__empty_payload(self, mock_generate_presigned_url: MagicMock) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        attachment = self.create_attachment(scheduled_email)
        self._logSuperuserIn()
        mock_generate_presigned_url.return_value = "TestPresignedUrl"

        # Act
        response = self.client.post(self.url(args=[attachment.pk]))

        # Assert
        self.assertEqual(response.status_code, 200)

    @patch("src.emails.controller.s3_client.generate_presigned_url")
    def test_generate_presigned_url__two_hours(self, mock_generate_presigned_url: MagicMock) -> None:
        # Arrange
        now = timezone.now()
        scheduled_email = self.create_scheduled_email(now)
        attachment = self.create_attachment(scheduled_email)
        self._logSuperuserIn()
        mock_generate_presigned_url.return_value = "TestPresignedUrl"

        # Act
        response = self.client.post(
            self.url(args=[attachment.pk]),
            {
                "expiration_seconds": 2 * 60 * 60,
            },
        )

        # Assert
        self.assertEqual(response.status_code, 200)
