import datetime
from django.core.management.base import BaseCommand, CommandError
from workshops.models import Event


class Command(BaseCommand):
    args = ''
    help = 'List slugs and URLs of all published events.'

    def handle(self, *args, **options):
        if len(args) != 0:
            raise CommandError('Usage: report_published_events')

        events = Event.objects.published_events()

        for e in events:
            print(e.slug, e.url)
