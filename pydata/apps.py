import re
import unittest

from django import forms
from django.apps import AppConfig
from django.utils.functional import curry


class PyDataConfig(AppConfig):
    name = 'pydata'
    label = 'PyData'
    verbose_name = 'AMY for PyData conferences'

    def ready(self):
        from . import checks

        from workshops.forms import PersonForm, TaskForm, SponsorshipForm
        from workshops.models import Person, Task, Organization, Sponsorship
        from workshops.test.base import TestBase
        from workshops.test.test_sponsorship import TestSponsorshipViews
        from workshops.views import EventCreate, PersonCreate

        # Add fixtures within pydata app to testing database
        TestBase.fixtures = [
            'workshops_organization.json', 'workshops_role.json']

        # Test for adding sponsor w/o amount should fail
        TestSponsorshipViews.test_add_sponsor_minimal = unittest.expectedFailure(
            TestSponsorshipViews.test_add_sponsor_minimal)

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

        # Add choices to `amount` field
        # Django migration system complains about missing migrations
        amount_field = Sponsorship._meta.get_field('amount')
        amount_field.choices = Sponsorship.LEVELS

        # Add method `get_amount_display` to Sponsorship to return the level
        setattr(
            Sponsorship,
            'get_amount_display',
            curry(Sponsorship._get_FIELD_display, field=amount_field)
        )

        # Override the `__str__` method to display level instead of amount
        def __str__(self):
            return '{}: {}'.format(self.organization, self.get_amount_display())
        Sponsorship.add_to_class('__str__', __str__)

        # Add a regex to obtain URL of conference and `pk` of sponsor instance
        Sponsorship.PROFILE_REGEX = re.compile(r'^(?P<url>.+?(?=/sponsors))/sponsors/(?P<id>\d+)/?') # noqa

        # Add "Import from URL" button to SponsorshipForm
        class Media:
            js = ('import_sponsor.js', )
        SponsorshipForm.Media = Media

        # Add a dropdown to the `amount` field on SponsorshipForm
        SponsorshipForm.base_fields['amount'] = forms.ChoiceField(
            choices=Sponsorship.LEVELS,
        )

        # Add a regex to obtain URL of conference and `pk` of presentation
        Task.PRESENTATION_REGEX = re.compile(r'^(?P<url>.+?(?=/schedule))/schedule/presentation/(?P<id>\d+)/?') # noqa

        # Add "Import from URL" button to TaskForm
        class Media:
            js = ('import_task.js', )
        TaskForm.Media = Media

        # Add a regex to obtain URL of conference and `pk` of speaker
        Person.PROFILE_REGEX = re.compile(r'^(?P<url>.+?(?=/speaker))/speaker/profile/(?P<id>[^/]+)/?') # noqa

        # Add "Import from URL" button to PersonForm on PersonCreate view
        PersonCreate.template_name = 'pydata/person_create_form.html'

        class Media:
            js = ('import_person.js', )
        PersonForm.Media = Media

        # Prepopulate fields on EventCreate view
        def get_initial(self):
            numfocus = Organization.objects.get(fullname='NumFOCUS')
            return {
                'administrator': numfocus,
                'assigned_to': self.request.user,
            }
        EventCreate.get_initial = get_initial
