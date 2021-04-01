from django.apps import AppConfig


class ConsentsConfig(AppConfig):
    name = "consents"
    label = "consents"
    verbose_name = "Consents"

    def ready(self):
        super().ready()
        from consents import signals  # noqa
