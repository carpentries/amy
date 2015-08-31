from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from rest_framework.test import APIClient


class Command(BaseCommand):
    args = 'no arguments'
    help = 'Display YAML for badges.'

    def handle(self, *args, **options):
        client = APIClient()
        response = client.get(reverse('api:export-badges'),
                              {'format': 'yaml'})
        print(response.content.decode('utf-8'))
