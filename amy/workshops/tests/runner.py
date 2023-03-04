import io
import logging
import sys

from django.test.runner import DiscoverRunner


class SilenceLogsRunner(DiscoverRunner):
    log_output: bool

    def __init__(self, **kwargs):
        self.log_output = kwargs.pop("log_output", False)
        super().__init__(**kwargs)

    @classmethod
    def add_arguments(cls, parser):
        """New argument to CLI to output loggers at the end of the suite."""
        super().add_arguments(parser)
        parser.add_argument(
            "--log-output",
            action="store_true",
            help="Prints logger entries after the test suite finishes.",
        )

    def setup_test_environment(self, **kwargs) -> None:
        logger = logging.getLogger("amy")

        for handler in logger.handlers:
            if not hasattr(handler, "stream"):
                continue

            new_io_stream = io.StringIO()
            setattr(handler, "stream", new_io_stream)

        return super().setup_test_environment(**kwargs)

    def teardown_test_environment(self, **kwargs) -> None:
        if self.log_output:
            print("---------------------- Logger output ----------------------")
            logger = logging.getLogger("amy")
            for handler in logger.handlers:
                try:
                    stream_value = handler.stream.getvalue()  # type: ignore
                    print(stream_value, file=sys.stderr)
                except AttributeError:
                    pass

        return super().teardown_test_environment(**kwargs)
