from django.apps import AppConfig


class EmailsConfig(AppConfig):
    default_auto_field = "django.db.models.UUIDField"
    name = "emails"

    def ready(self) -> None:
        # Autoconnect signal receivers using `@receiver` decorator
        from emails import actions  # noqa
