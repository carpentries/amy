from django.apps import AppConfig


class ConsentsConfig(AppConfig):
    name = "src.consents"
    label = "consents"
    verbose_name = "Consents"

    def ready(self) -> None:
        super().ready()
        from src.consents import receivers  # noqa
