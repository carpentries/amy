import sys
import os
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from workshops.models import Award, Badge, Person


class Command(BaseCommand):
    args = '/path/to/certificates'
    help = 'Report inconsistencies in PDF certificates.'

    def add_arguments(self, parser):
        parser.add_argument(
            'path', help='Path to root directory of certificates repository',
        )

    def handle(self, *args, **options):
        '''Main entry point.'''

        path_to_root = options['path']

        badges = self.get_badges()
        for (name, badge) in badges:
            db_people = self.get_db_people(badge)
            cert_path = os.path.join(path_to_root, name)
            if not os.path.isdir(cert_path):
                print('No directory {0}'.format(name))
            else:
                file_people = self.get_file_people(cert_path)
                self.report_missing('database but not disk', name, db_people - file_people)
                self.report_missing('disk but not database', name, file_people - db_people)

    def get_badges(self):
        '''Get all available badges as list of lower-case name and badge pairs.'''

        return [(b.name.lower(), b) for b in Badge.objects.all()]

    def get_db_people(self, badge):
        '''Get set of usernames of all people with the given badge.'''

        return set(Award.objects.filter(badge=badge).values_list('person__username', flat=True))

    def get_file_people(self, path):
        '''Get names of all people with the given certificate.'''

        return set([os.path.splitext(e)[0]
                    for e in os.listdir(path)
                    if e.endswith('.pdf')])

    def report_missing(self, title, kind, items):
        '''Report missing items.'''
        if items:
            print('{0} {1}'.format(kind, title))
            for i in sorted(list(items)):
                try:
                    p = Person.objects.get(username=i)
                    print(' {0}: {1}'.format(i, p))
                except Person.DoesNotExist:
                    print(' {0}'.format(i))
