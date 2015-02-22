from django.core.management.base import BaseCommand, CommandError
from workshops.util import upload_person_task_csv

class Command(BaseCommand):
    args = 'filename'
    help = 'Upload users and roles from the given CSV files.'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('No CSV filename specified')
        filename = args[0]

        try:
            with open(filename, 'r') as reader:
                persons_tasks, empty_fields = upload_person_task_csv(reader)
        except Exception as e:
            raise CommandError('Failed to read CSV file: {0}'.format(str(e)))

        if empty_fields:
            missing = ', '.join(empty_fields)
            raise CommandError('Missing field(s) in {0}: {1}'.format(filename, missing))
