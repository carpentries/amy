import yaml
from django.core.management.base import BaseCommand, CommandError
from workshops.views import _export_badges

class Command(BaseCommand):
    args = 'no arguments'
    help = 'Display YAML for badges.'

    def handle(self, *args, **options):
        print(yaml.dump(_export_badges()).rstrip())
