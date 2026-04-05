from unittest.mock import MagicMock

from django.http import HttpRequest
from django.test import RequestFactory, TestCase, override_settings

from src.offering.conditions import not_in_production_condition

FLAG_NAME = "SERVICE_OFFERING"


def _make_request(path: str = "/") -> HttpRequest:
    """RequestFactory request with a mock authenticated user and empty session.

    The anonymous and session conditions on SERVICE_OFFERING require these
    attributes to be present on the request object.
    """
    request = RequestFactory().get(path)
    request.user = MagicMock(is_anonymous=False)
    request.session = {}  # type: ignore[assignment]
    return request


class TestNotInProductionCondition(TestCase):
    """Unit tests for the not_in_production custom flag condition."""

    @override_settings(PROD_ENVIRONMENT=True)
    def test_returns_false_in_production(self) -> None:
        """Condition evaluates to False when PROD_ENVIRONMENT is True."""
        self.assertFalse(not_in_production_condition(True))

    @override_settings(PROD_ENVIRONMENT=False)
    def test_returns_true_outside_production(self) -> None:
        """Condition evaluates to True when PROD_ENVIRONMENT is False."""
        self.assertTrue(not_in_production_condition(True))
