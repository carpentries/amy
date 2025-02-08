import logging
from typing import Any, Callable

from flags.state import flag_enabled

logger = logging.getLogger("amy")


def feature_flag_enabled(feature_flag: str) -> Callable:
    """Check if the feature flag is enabled before running the function.
    If the feature flag is disabled, the function will exit early and not run."""

    def func_wrapper(func: Callable[..., Any]) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            request = kwargs.get("request")
            if not request:
                logger.debug(
                    f"Cannot check {feature_flag} feature flag, `request` parameter " f"to {func.__name__} is missing"
                )
                return

            if not flag_enabled(feature_flag, request=request):
                logger.debug(f"{feature_flag} feature flag not set, skipping {func.__name__}")
                return

            return func(*args, **kwargs)

        return wrapper

    return func_wrapper
