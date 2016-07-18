from django.apps import apps, AppConfig
from django.utils.functional import curry


class PyDataConfig(AppConfig):
    name = 'pydata'
    label = 'PyData'
    verbose_name = 'AMY for PyData conferences'

    def ready(self):
        from . import checks

        Sponsorship = apps.get_model('workshops', 'Sponsorship')
        # Add choices to the `amount` field
        Sponsorship.LEVELS = (
            (0, 'Founding'),
            (15000, 'Diamond'),
            (8000, 'Platinum'),
            (5000, 'Gold'),
            (3000, 'Silver'),
            (1500, 'Supporting'),
            (1, 'Community'),
        )
        amount_field = Sponsorship._meta.get_field('amount')
        amount_field.choices = Sponsorship.LEVELS
        amount_field.verbose_name = 'Sponsorship level'

        # Add an attribute to sponsorship object to return the level text
        # Mimics `get_amount_choice` method
        # See https://github.com/django/django/blob/49b4596cb4744e4b68d56e6a540a3e15c1582963/django/db/models/fields/__init__.py#L702
        setattr(
            Sponsorship,
            'level',
            curry(Sponsorship._get_FIELD_display, field=amount_field),
        )
