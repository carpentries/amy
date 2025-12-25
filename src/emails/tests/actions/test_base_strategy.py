from unittest.mock import MagicMock

from django.http import HttpRequest
from django.test import TestCase

from src.emails.actions.base_strategy import run_strategy
from src.emails.actions.exceptions import EmailStrategyException
from src.emails.types import StrategyEnum


class TestRunStrategy(TestCase):
    def test_error_when_strategy_not_in_mapping(self) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        # Act & Assert
        with self.assertRaisesMessage(EmailStrategyException, f"Unknown strategy {strategy}"):
            run_strategy(
                strategy,
                {},
                HttpRequest(),
                sender=None,
            )

    def test_noop_strategy_does_nothing(self) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP

        # Act
        run_strategy(
            strategy,
            {StrategyEnum.NOOP: None},
            HttpRequest(),
            sender=None,
        )

    def test_correct_strategy_sends_signal(self) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        signal = MagicMock()
        request = HttpRequest()

        # Act
        run_strategy(
            strategy,
            {StrategyEnum.CREATE: signal},
            request,
            sender=None,
            arg1="value1",
            arg2="value2",
        )

        # Assert
        signal.send.assert_called_once_with(
            sender=None,
            request=request,
            arg1="value1",
            arg2="value2",
        )
