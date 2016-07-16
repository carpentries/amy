from django.apps import apps, AppConfig


class PyDataConfig(AppConfig):
    name = 'pydata'
    label = 'PyData'
    verbose_name = 'AMY for PyData conferences'

    def ready(self):
        from . import checks
