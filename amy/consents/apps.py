from django.apps import AppConfig


class ConsentsConfig(AppConfig):
    name = "consents"
    label = "consents"
    verbose_name = "Consents"

    def ready(self) -> None:
        super().ready()
        from consents import receivers  # noqa
