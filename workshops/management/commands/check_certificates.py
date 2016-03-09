import sys
import os
import csv
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from workshops.models import Award, Badge, Person


class Command(BaseCommand):
    help = 'Report inconsistencies in PDF certificates.'

    def add_arguments(self, parser):
        parser.add_argument(
            'path', help='Path to root directory of certificates repository',
        )

    def handle(self, *args, **options):
        '''Main entry point.'''

        path_to_root = options['path']

        badges = self.get_badges()
        result = [['which','badge','event','username','person','email','awarded']]
        for (name, badge) in badges:
            db_records = self.get_db_records(badge)
            db_people = db_records.keys()
            cert_path = os.path.join(path_to_root, name)
            if not os.path.isdir(cert_path):
                print('No directory {0}'.format(name), file=sys.stderr)
            else:
                file_people = self.get_file_people(cert_path)
                self.missing(result, 'database-disk', name, db_people - file_people, db_records)
                self.missing(result, 'disk-database', name, file_people - db_people, db_records)
        csv.writer(sys.stdout).writerows(result)

    def get_badges(self):
        '''Get all available badges as list of lower-case name and badge pairs.'''

        return [(b.name.lower(), b) for b in Badge.objects.all()]

    def get_db_records(self, badge):
        '''Get set of usernames of all people with the given badge.'''

        objects = Award.objects.filter(badge=badge).values_list('person__username', 'awarded', 'event__slug')
        return dict((obj[0], {'awarded': obj[1], 'event': obj[2]}) for obj in objects)

    def get_file_people(self, path):
        '''Get names of all people with the given certificate.'''

        return set([os.path.splitext(e)[0]
                    for e in os.listdir(path)
                    if e.endswith('.pdf')])

    def missing(self, report, title, kind, usernames, records):
        '''Report missing usernames.'''
        for uid in usernames:
            try:
                p = Person.objects.get(username=uid)
                name = p.get_full_name()
                email = p.email
                event, awarded = '', ''
                if uid in records:
                    event = records[uid]['event']
                    awarded = records[uid]['awarded']
                report.append([title, kind, event, uid, p.get_full_name(), p.email, awarded])
            except Person.DoesNotExist:
                print('{0}'.format(uid), file=sys.stderr)
