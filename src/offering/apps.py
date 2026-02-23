from django.apps import AppConfig


class OfferingConfig(AppConfig):
    name = "src.offering"

    def ready(self) -> None:
        from src.offering import conditions  # noqa: F401
