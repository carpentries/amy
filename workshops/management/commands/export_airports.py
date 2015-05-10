import yaml
from django.core.management.base import BaseCommand, CommandError
from workshops.views import _export_instructors

class Command(BaseCommand):
    args = 'no arguments'
    help = 'Display YAML for airports.'

    def handle(self, *args, **options):
        print(yaml.dump(_export_instructors()).rstrip())
