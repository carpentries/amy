from collections import namedtuple

from django.core.management.base import BaseCommand, CommandError
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from workshops.models import Event


class Command(BaseCommand):
    help = 'Import location and contact data from historical workshops.'

    # only one entry has this issue
    TRANSLATE_COUNTRY = {
        'UNITED STATES': 'US',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            'filename', help='YAML archive of past workshops',
        )
        parser.add_argument(
            '--overwrite', action='store_true', default=False,
            help='Overwrite values in non-empty fields [default: skip]',
        )

    def compare_and_update(self, event, workshop, overwrite=False):
        fields = workshop._fields

        for field in fields:
            L = getattr(event, field)
            R = getattr(workshop, field)
            if R:
                if overwrite or not L:
                    # update only if there's a new value (R) and we agreed to
                    # overwrite existing value OR there's a new value (R) and
                    # previous value is empty
                    setattr(event, field, R)
        event.save()

    def handle(self, *args, **options):
        filename = options['filename']
        overwrite = options['overwrite']

        with open(filename, 'r') as f:
            data = load(f, Loader=Loader)

        Workshop = namedtuple(
            'Workshop',
            ['slug', 'contact', 'country', 'venue', 'address', 'latitude',
             'longitude']
        )

        data = [
            Workshop(
                slug=D.get('slug'), contact=D.get('contact'),
                country=D.get('country', '').upper(),
                venue=D.get('venue'), address=D.get('address'),
                latitude=(D.get('latlng') or ',').split(',')[0],
                longitude=(D.get('latlng') or ',').split(',')[1],
            )
            for D in data
        ]

        for workshop in data:
            try:
                event = Event.objects.get(slug=workshop.slug)
                country_repl = self.TRANSLATE_COUNTRY.get(workshop.country)
                if country_repl:
                    workshop = workshop._replace(country=country_repl)
                self.compare_and_update(event, workshop, overwrite)
            except Event.DoesNotExist:
                self.stderr.write('Historical event {} does not exist in the'
                                  ' database'.format(workshop.slug))
