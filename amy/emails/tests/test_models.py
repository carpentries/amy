from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

from emails.models import EmailTemplate


class TestEmailTemplate(TestCase):
    def test_get_engine__default(self) -> None:
        # Arrange
        expected_engine_name = settings.EMAIL_TEMPLATE_ENGINE_BACKEND
        # Act
        result = EmailTemplate.get_engine()
        # Assert
        self.assertEqual(EmailTemplate.get_engine(expected_engine_name), result)

    def test_validate_template__correct(self) -> None:
        # Arrange
        template = "Hello, {{ name }}{% if lastname %} {{ lastname }}{% endif %}."
        context = {
            "name": "James",
            "lastname": "Bond",
        }
        engine = EmailTemplate.get_engine()

        # Act
        result = EmailTemplate.validate_template(engine, template, context)

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
            EmailTemplate.validate_template(engine, template, context)

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
