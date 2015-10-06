import sys
import csv
from django.core.management.base import BaseCommand, CommandError
from workshops.models import Event


class Command(BaseCommand):
    args = ''
    help = 'Report all financial activity related to invoicing.'

    def handle(self, *args, **options):
        if len(args) != 0:
            raise CommandError('Usage: report_invoicing')

        events = Event.objects.filter(admin_fee__gt=0).filter(start__isnull=False).order_by('slug')

        records = [['event', 'fee', 'paid']]
        for e in events:
            records.append([e.slug, e.admin_fee, e.invoice_status])

        writer = csv.writer(sys.stdout)
        writer.writerows(records)
