import yaml

from django.core.management.base import BaseCommand
from api.views import ExportBadgesView


class Command(BaseCommand):
    args = 'no arguments'
    help = 'Display YAML for badges.'

    def handle(self, *args, **options):
        view = ExportBadgesView()
        response = view.get(None, format='yaml')
        print(yaml.dump(response.data))
