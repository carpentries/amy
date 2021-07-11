from django.test import TestCase

from workshops.filters import extend_country_choices


class TestExtendCountryChoices(TestCase):
    def test_no_overrides(self):
        # Arrange
        choices = ["PL", "US", "GB", "W3"]
        overrides = {}

        # Act
        results = extend_country_choices(choices, overrides)

        # Assert
        self.assertEqual(choices, results)

    def test_no_common_overrides(self):
        # Arrange
        choices = ["PL", "US", "GB"]
        overrides = {"W3": "Online"}

        # Act
        results = extend_country_choices(choices, overrides)

        # Assert
        self.assertEqual(choices, results)

    def test_overrides(self):
        # Arrange
        choices = ["PL", "US", "GB", "W3"]
        overrides = {"W3": "Online"}

        # Act
        results = extend_country_choices(choices, overrides)

        # Assert
        self.assertEqual(
            results,
            [
                "PL",
                "US",
                "GB",
                ("W3", "Online"),
            ],
        )
