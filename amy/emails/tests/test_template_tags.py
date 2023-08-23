from unittest.mock import MagicMock

from django.test import TestCase

from emails.templatetags.emails import model_documentation_link


class TestModelDocumentationLink(TestCase):
    def test_model_documentation_link__valid_model(self) -> None:
        # Arrange
        # Real models are replaced with their metaclass BaseModel, so the tests don't
        # work with real models and instead mocks are used.
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
        # Real models are replaced with their metaclass BaseModel, so the tests don't
        # work with real models and instead mocks are used.
        model = MagicMock()
        # Badge is not in the mapping yet
        model.__class__.__name__ = "Badge"

        # Act
        link = model_documentation_link(model)

        # Assert
        self.assertEqual(link, "")
