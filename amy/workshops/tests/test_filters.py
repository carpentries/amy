from unittest.mock import MagicMock

from django.test import TestCase

from workshops.filters import (
    AllCountriesFilter,
    AllCountriesMultipleFilter,
    extend_country_choices,
)


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


class TestAllCountriesFilterCustomCountries(TestCase):
    def test_extra_choices(self):
        """Regression test for https://github.com/carpentries/amy/issues/1996."""
        # Arrange
        filter_ = AllCountriesFilter()
        filter_._get_countries = MagicMock(return_value=["PL", "US", "GB", "W3", "EU"])

        # Act
        filter_.field

        # Assert
        self.assertEqual(
            filter_.extra["choices"],
            [
                ("EU", "European Union"),
                ("W3", "Online"),
                ("PL", "Poland"),
                ("GB", "United Kingdom"),
                ("US", "United States"),
            ],
        )


class TestAllCountriesMultipleFilterCustomCountries(TestCase):
    def test_extra_choices(self):
        """Regression test for https://github.com/carpentries/amy/issues/1996."""
        # Arrange
        filter_ = AllCountriesMultipleFilter()
        filter_._get_countries = MagicMock(return_value=["PL", "US", "GB", "W3", "EU"])

        # Act
        filter_.field

        # Assert
        self.assertEqual(
            filter_.extra["choices"],
            [
                ("EU", "European Union"),
                ("W3", "Online"),
                ("PL", "Poland"),
                ("GB", "United Kingdom"),
                ("US", "United States"),
            ],
        )
