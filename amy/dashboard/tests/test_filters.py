from typing import Any
from unittest.mock import ANY, MagicMock, call

from django.core.exceptions import ValidationError
from django.db.models import F
from django.test import TestCase

from dashboard.filters import UpcomingTeachingOpportunitiesFilter


class TestUpcomingTeachingOpportunitiesFilter(TestCase):
    def test_fields(self) -> None:
        # Arrange
        data: dict[str, Any] = {}
        # Act
        filterset = UpcomingTeachingOpportunitiesFilter(data)
        # Assert
        self.assertEqual(
            filterset.filters.keys(),
            {"status", "order_by", "only_applied_to", "country", "curricula"},
        )

    def test_invalid_values_for_status(self) -> None:
        # Arrange
        test_data = [
            "test",
            "online/inperson",
            " online",
        ]
        filterset = UpcomingTeachingOpportunitiesFilter({})
        field = filterset.filters["status"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert
                with self.assertRaises(ValidationError):
                    field.validate(value)

    def test_valid_values_for_status(self) -> None:
        # Arrange
        test_data = [
            "",
            None,
            "online",
            "inperson",
        ]
        filterset = UpcomingTeachingOpportunitiesFilter({})
        field = filterset.filters["status"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert no exception
                field.validate(value)

    def test_invalid_values_for_order_by(self) -> None:
        # Arrange
        test_data = [
            "event_start",  # single _ instead of double __
            "-event__end",
            "distance",
            " proximity",  # space
        ]
        filterset = UpcomingTeachingOpportunitiesFilter({})
        field = filterset.filters["order_by"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert
                with self.assertRaises(ValidationError):
                    field.validate(value)

    def test_valid_values_for_order_by(self) -> None:
        # Arrange
        test_data = [
            "",
            None,
            "event__start",
            "-event__start",
            "proximity",
            "-proximity",
        ]
        filterset = UpcomingTeachingOpportunitiesFilter({})
        field = filterset.filters["order_by"].field
        # Act
        for value in test_data:
            with self.subTest(value=value):
                # Assert no exception
                field.validate(value)

    def test_filter_status__online(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        name = "status"
        # Act
        filterset.filter_status(qs_mock, name, "online")
        # Assert
        qs_mock.filter.assert_called_once_with(event__tags__name="online")
        qs_mock.exclude.assert_not_called()

    def test_filter_status__inperson(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        name = "status"
        # Act
        filterset.filter_status(qs_mock, name, "inperson")
        # Assert
        qs_mock.filter.assert_not_called()
        qs_mock.exclude.assert_called_once_with(event__tags__name="online")

    def test_filter_status__other_value(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        name = "status"
        # Act
        result = filterset.filter_status(qs_mock, name, "other")
        # Assert
        qs_mock.filter.assert_not_called()
        qs_mock.exclude.assert_not_called()
        self.assertEqual(result, qs_mock)

    def test_filter_order_by__not_proximity(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        name = "order_by"
        # Act
        filterset.filter_order_by(qs_mock, name, ["another value"])
        # Assert
        qs_mock.annotate.assert_not_called()
        qs_mock.order_by.assert_called_once_with("another value")

    def test_filter_order_by__proximity(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        name = "order_by"
        # Act
        filterset.filter_order_by(qs_mock, name, ["proximity"])
        # Assert
        qs_mock.annotate.assert_called_once_with(distance=ANY)
        qs_mock.annotate().order_by.assert_called_once_with("distance")

    def test_filter_order_by__neg_proximity(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        name = "order_by"
        # Act
        filterset.filter_order_by(qs_mock, name, ["-proximity"])
        # Assert
        qs_mock.annotate.assert_called_once_with(distance=ANY)
        qs_mock.annotate().order_by.assert_called_once_with("-distance")

    def test_filter_order_by__latlng_provided(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        filterset.request = MagicMock()
        filterset.request.user.airport_iata = "KRK"
        name = "order_by"
        distance_expression = (F("event__latitude") - 123.4) ** 2 + (F("event__longitude") - 56.7) ** 2
        # Act
        filterset.filter_order_by(qs_mock, name, ["proximity"])
        # Assert
        self.assertEqual(qs_mock.annotate.call_args_list[0], call(distance=distance_expression))

    def test_filter_application_only__not_applied(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        name = "only_applied_to"
        # Act
        filterset.filter_application_only(qs_mock, name, False)
        # Assert
        qs_mock.filter.assert_not_called()

    def test_filter_application_only__applied(self) -> None:
        # Arrange
        qs_mock = MagicMock()
        filterset = UpcomingTeachingOpportunitiesFilter({})
        filterset.request = MagicMock()
        name = "only_applied_to"
        # Act
        filterset.filter_application_only(qs_mock, name, True)
        # Assert
        qs_mock.filter.assert_called_once_with(signups__person=filterset.request.user)
