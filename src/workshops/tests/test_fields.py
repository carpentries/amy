from django.core.exceptions import ValidationError

from src.workshops.fields import NullableGithubUsernameField, Select2TagWidget
from src.workshops.tests.base import TestBase


class TestNullableGHUsernameField(TestBase):
    def setUp(self) -> None:
        self.passing = [
            "harrypotter",
            "hp",
            "hpotter",
            "harry-potter",
            "harry-potter123",
            "Harry-Potter",
            "",
            None,
        ]

        self.failing = [
            "harry_potter",
            "harry--potter",
            "-harry",
            "potter-",
            "harry-averyveryverylongmiddlename-potter",
        ]

        self.field = NullableGithubUsernameField()

    def test_passing_usernames(self) -> None:
        """All correct usernames pass the field validation."""
        for username in self.passing:
            self.field.run_validators(username)

    def test_failing_usernames(self) -> None:
        """All incorrect usernames don't pass the field validation."""
        for username in self.failing:
            with self.assertRaises(ValidationError):
                self.field.run_validators(username)


class TestSelect2TagWidget(TestBase):
    def setUp(self) -> None:
        self.widget = Select2TagWidget()

    def test_optgroups(self) -> None:
        # incorrect input
        self.assertEqual(self.widget.optgroups("name", []), [(None, [], 0)])

        # correct input (1 value)
        option1 = self.widget.create_option("name", "Harry", "Harry", True, 0)
        self.assertEqual(
            self.widget.optgroups("name", ["Harry"]),
            [
                (
                    None,
                    [option1],
                    0,
                )
            ],
        )

        # correct input (2 values)
        option1 = self.widget.create_option("name", "Harry", "Harry", True, 0)
        option2 = self.widget.create_option("name", "Ron", "Ron", True, 1)
        self.assertEqual(
            self.widget.optgroups("name", ["Harry;Ron"]),
            [
                (
                    None,
                    [option1, option2],
                    0,
                )
            ],
        )
