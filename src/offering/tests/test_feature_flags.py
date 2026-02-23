from typing import Any, cast
from unittest.mock import MagicMock

from django.conf import settings
from django.http import HttpRequest
from django.test import RequestFactory, TestCase, override_settings
from flags.state import flag_enabled  # type: ignore[import-untyped]

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


class TestServiceOfferingFlagProductionGuard(TestCase):
    """Verify that the SERVICE_OFFERING flag cannot be enabled in production."""

    @override_settings(PROD_ENVIRONMENT=True)
    def test_flag_disabled_in_production_without_parameter(self) -> None:
        """Flag is disabled in production even without the enabling parameter."""
        self.assertFalse(flag_enabled(FLAG_NAME, request=_make_request("/")))

    @override_settings(PROD_ENVIRONMENT=True)
    def test_flag_disabled_in_production_with_enabling_parameter(self) -> None:
        """Flag stays disabled in production even when the enabling URL parameter is present."""
        self.assertFalse(flag_enabled(FLAG_NAME, request=_make_request("/?enable_service_offering=true")))

    @override_settings(PROD_ENVIRONMENT=False)
    def test_flag_can_be_enabled_in_non_production_via_parameter(self) -> None:
        """Flag can be enabled in non-production environments via URL parameter."""
        self.assertTrue(flag_enabled(FLAG_NAME, request=_make_request("/?enable_service_offering=true")))

    @override_settings(PROD_ENVIRONMENT=False)
    def test_flag_disabled_in_non_production_without_parameter(self) -> None:
        """Flag is still disabled in non-production when no enabling condition is present."""
        self.assertFalse(flag_enabled(FLAG_NAME, request=_make_request("/")))

    def test_settings_have_required_not_in_production_condition(self) -> None:
        """SERVICE_OFFERING flag in settings has a required not_in_production condition."""
        conditions = cast(list[Any], settings.FLAGS[FLAG_NAME])
        required = [
            c
            for c in conditions
            if isinstance(c, dict) and c.get("condition") == "not_in_production" and c.get("required") is True
        ]
        self.assertEqual(len(required), 1)
