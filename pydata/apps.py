import re

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

        # Add "Import from URL" button to SponsorshipForm
        from workshops.forms import SponsorshipForm

        class Media:
            js = ('import_sponsor.js', )

        SponsorshipForm.Media = Media

        setattr(
            Sponsorship,
            'PROFILE_REGEX',
            re.compile(r'^(?P<url>.+?(?=/sponsors))/sponsors/(?P<id>[^/]+)/?'),
        )

        Task = apps.get_model('workshops', 'Task')
        setattr(
            Task,
            'PRESENTATION_REGEX',
            re.compile(r'^(?P<url>.+?(?=/schedule))/schedule/presentation/(?P<id>[^/]+)/?'),
        )

        Person = apps.get_model('workshops', 'Person')
        setattr(
            Person,
            'PROFILE_REGEX',
            re.compile(r'^(?P<url>.+?(?=/speaker))/speaker/profile/(?P<id>[^/]+)/?'),
        )

        # Add "Import from URL" button to PersonForm on PersonCreate view
        from workshops.forms import PersonForm
        from workshops.views import PersonCreate

        class Media:
            js = ('import_person.js', )

        PersonForm.Media = Media
        PersonCreate.template_name = 'pydata/person_create_form.html'

        # Add "Import from URL" button to TaskForm on TaskCreate view
        from workshops.forms import TaskForm
        from workshops.views import TaskCreate

        class Media:
            js = ('import_task.js', )

        TaskForm.Media = Media
        TaskCreate.template_name = 'pydata/task_create_form.html'
