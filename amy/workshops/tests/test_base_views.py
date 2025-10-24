from typing import Any
from unittest.mock import patch

from django.http import HttpRequest, HttpResponseBase
from django.http.response import Http404
from django.test import TestCase

from workshops.base_views import ConditionallyEnabledMixin


class FakeView:
    """Used in the tests below."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        raise NotImplementedError()


class TestConditionallyEnabledView(TestCase):
    def test_disabled_view_through_parameter(self) -> None:
        # Arrange
        class View(ConditionallyEnabledMixin, FakeView):
            pass

        view = View()
        view.view_enabled = False

        # Act & Assert
        with patch.object(FakeView, "dispatch") as mock_dispatch:
            with self.assertRaises(Http404):
                view.dispatch(None)  # type: ignore[arg-type]
            mock_dispatch.assert_not_called()

    def test_disabled_view_through_method(self) -> None:
        # Arrange
        class View(ConditionallyEnabledMixin, FakeView):
            def get_view_enabled(self, request: HttpRequest) -> bool:
                return False

        view = View()

        # Act & Assert
        with patch.object(FakeView, "dispatch") as mock_dispatch:
            with self.assertRaises(Http404):
                view.dispatch(None)  # type: ignore[arg-type]
            mock_dispatch.assert_not_called()

    def test_enabled_view_through_parameter(self) -> None:
        # Arrange
        class View(ConditionallyEnabledMixin, FakeView):
            pass

        view = View()
        view.view_enabled = True

        with patch.object(FakeView, "dispatch") as mock_dispatch:
            # Act
            view.dispatch(None)  # type: ignore[arg-type]

            # Assert
            mock_dispatch.assert_called_once()

    def test_enabled_view_through_method(self) -> None:
        # Arrange
        class View(ConditionallyEnabledMixin, FakeView):
            def get_view_enabled(self, request: HttpRequest) -> bool:
                return True

        view = View()

        with patch.object(FakeView, "dispatch") as mock_dispatch:
            # Act
            view.dispatch(None)  # type: ignore[arg-type]

            # Assert
            mock_dispatch.assert_called_once()
