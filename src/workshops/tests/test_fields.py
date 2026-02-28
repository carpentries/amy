from django.core.exceptions import ValidationError

from src.workshops.consts import COUNTRIES, IATA_AIRPORTS
from src.workshops.fields import AirportSelect2Widget, NullableGithubUsernameField, Select2TagWidget
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


class TestAirportSelect2Widget(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self.widget = AirportSelect2Widget()  # type: ignore[no-untyped-call]

    def test_data_view(self) -> None:
        """Widget is pre-configured to use the airports lookup view."""
        self.assertEqual(self.widget.data_view, "airports-lookup")

    def test_optgroups_empty_string(self) -> None:
        """Empty string value delegates to parent — no airport option is injected."""
        result = self.widget.optgroups("airport_iata", [""])
        # Parent returns one group with a blank option; verify no IATA code was injected.
        self.assertEqual(len(result), 1)
        _, options, _ = result[0]
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["value"], "")

    def test_optgroups_empty_list(self) -> None:
        """Empty value list delegates to parent — no airport option is injected."""
        result = self.widget.optgroups("airport_iata", [])
        # Parent returns one group with a blank option; verify no IATA code was injected.
        self.assertEqual(len(result), 1)
        _, options, _ = result[0]
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["value"], "")

    def test_optgroups_known_iata_code(self) -> None:
        """A known IATA code yields a single pre-selected option with the full display label."""
        iata_code = "KRK"
        airport = IATA_AIRPORTS[iata_code]
        expected_label = f"{iata_code}: {airport['name']} ({COUNTRIES.get(airport['country'], '-')}, {airport['tz']})"
        expected_option = self.widget.create_option("airport_iata", iata_code, expected_label, True, 0)

        result = self.widget.optgroups("airport_iata", [iata_code])

        self.assertEqual(result, [(None, [expected_option], 0)])

    def test_optgroups_unknown_iata_code(self) -> None:
        """An unrecognised IATA code falls back to using the raw IATA code as the label."""
        iata_code = "ZZZ"
        expected_option = self.widget.create_option("airport_iata", iata_code, iata_code, True, 0)

        result = self.widget.optgroups("airport_iata", [iata_code])

        self.assertEqual(result, [(None, [expected_option], 0)])
