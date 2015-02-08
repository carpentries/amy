from django.core.management.base import BaseCommand, CommandError
from workshops.models import Person

class Command(BaseCommand):
    args = 'no arguments'
    help = 'Create a superuser called "admin" with password "admin".'

    def handle(self, *args, **options):
        try:
            Person.objects.create_superuser(username='admin',
                                            personal='admin',
                                            family='admin',
                                            email='admin@example.org',
                                            password='admin')
        except Exception as e:
            raise CommandError('Failed to create admin: {0}'.format(str(e)))
