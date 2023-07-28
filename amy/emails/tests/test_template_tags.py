from unittest.mock import MagicMock

from django.test import TestCase

from emails.templatetags.emails import is_email_module_enabled, model_documentation_link


class TestEmailsTemplateTags(TestCase):
    def test_feature_flag_enabled(self) -> None:
        with self.settings(EMAIL_MODULE_ENABLED=False):
            self.assertEqual(is_email_module_enabled(), False)
        with self.settings(EMAIL_MODULE_ENABLED=True):
            self.assertEqual(is_email_module_enabled(), True)


class TestModelDocumentationLink(TestCase):
    def test_model_documentation_link__valid_model(self) -> None:
        # Arrange
        model = MagicMock()
        model.__class__.__name__ = "Person"

        # Act
        link = model_documentation_link(model)

        # Assert
        self.assertEqual(
            link,
            "https://carpentries.github.io/amy/amy_database_structure/#persons",
        )

    def test_model_documentation_link__invalid_model(self) -> None:
        # Arrange
        model = MagicMock()
        # Badge is not in the mapping yet
        model.__class__.__name__ = "Badge"

        # Act
        link = model_documentation_link(model)

        # Assert
        self.assertEqual(link, "")
