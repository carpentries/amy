from argparse import ArgumentParser
import io
import logging
import sys
from typing import Any

from django.test.runner import DiscoverRunner


class SilenceLogsRunner(DiscoverRunner):
    log_output: bool

    def __init__(self, **kwargs: Any) -> None:
        self.log_output = kwargs.pop("log_output", False)
        super().__init__(**kwargs)

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        """New argument to CLI to output loggers at the end of the suite."""
        super().add_arguments(parser)
        parser.add_argument(
            "--log-output",
            action="store_true",
            help="Prints logger entries after the test suite finishes.",
        )

    def get_all_loggers(self) -> list[logging.Logger]:
        root_logger = logging.getLogger()
        return [root_logger] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]

    def print_handler_stream_to_stderr(self, handler: logging.StreamHandler[Any]) -> None:
        stream_value = handler.stream.getvalue()
        if stream_value:
            print(stream_value, file=sys.stderr)

    def setup_test_environment(self, **kwargs: Any) -> None:
        loggers = self.get_all_loggers()
        for logger in loggers:
            for handler in logger.handlers:
                if not isinstance(handler, logging.StreamHandler):
                    continue

                handler.stream = io.StringIO()

        return super().setup_test_environment(**kwargs)

    def teardown_test_environment(self, **kwargs: Any) -> None:
        if self.log_output:
            print("--------------------------- Logger output ----------------------------")
            loggers = self.get_all_loggers()
            for logger in loggers:
                for handler in logger.handlers:
                    if not isinstance(handler, logging.StreamHandler):
                        continue

                    self.print_handler_stream_to_stderr(handler)

        return super().teardown_test_environment(**kwargs)
