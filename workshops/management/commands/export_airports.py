import yaml

from django.core.management.base import BaseCommand
from api.views import ExportInstructorLocationsView


class Command(BaseCommand):
    args = 'no arguments'
    help = 'Display YAML for airports.'

    def handle(self, *args, **options):
        view = ExportInstructorLocationsView()
        response = view.get(None, format='yaml')
        print(yaml.dump(response.data))
