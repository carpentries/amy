import logging
from typing import Any

from django.http import HttpRequest

from emails.actions.exceptions import EmailStrategyException
from emails.signals import Signal
from emails.types import StrategyEnum

logger = logging.getLogger("amy")


def run_strategy(
    strategy: StrategyEnum,
    signal_mapping: dict[StrategyEnum, Signal | None],
    request: HttpRequest,
    sender: Any,
    **kwargs: Any,
) -> None:
    if strategy not in signal_mapping:
        raise EmailStrategyException(f"Unknown strategy {strategy}")

    signal = signal_mapping[strategy]

    if not signal:
        logger.debug(f"Strategy {strategy} for {sender} is a no-op")
        return

    logger.debug(f"Sending signal for {sender} as result of strategy {strategy}")
    signal.send(
        sender=sender,
        request=request,
        **kwargs,
    )
