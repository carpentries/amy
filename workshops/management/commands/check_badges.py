import sys
import os
import glob
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from workshops.models import Badge, Award

class Command(BaseCommand):
    args = '/path/to/site'
    help = 'Report inconsistencies in badges.'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Usage: check_badges /path/to/site')

        path_to_site = args[0]
        badge_dir = os.path.join(path_to_site, 'badges')
        for entry in os.listdir(badge_dir):
            entry_path = os.path.join(badge_dir, entry)
            if os.path.isdir(entry_path):
                self.check_badges(entry, entry_path)

    def check_badges(self, badge_name, badge_path):
        try:
            badge = Badge.objects.get(name=badge_name)
            db_awards = set([a.person.username for a in Award.objects.filter(badge=badge)])
            path_awards = set([os.path.splitext(p)[0] for p in os.listdir(badge_path) if p.endswith('.json')])
            self.report_missing('in database but not site', badge_name, db_awards - path_awards)
            self.report_missing('in site but not database', badge_name, path_awards - db_awards)
        except ObjectDoesNotExist:
            print('badge "{0}" not known'.format(badge_name, file=sys.stderr))

    def report_missing(self, title, badge_name, items):
        if items:
            print('{0} {1}'.format(badge_name, title))
            for i in sorted(list(items)):
                print(' ', i)
