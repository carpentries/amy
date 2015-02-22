from django.core.management.base import BaseCommand, CommandError
from workshops.util import upload_person_task_csv

class Command(BaseCommand):
    args = 'filename'
    help = 'Upload users and roles from the given CSV files.'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('No CSV filename specified')
        try:
            with open(args[0], 'r') as reader:
                persons_tasks, empty_fields = upload_person_task_csv(reader)
        except Exception as e:
            raise CommandError('Failed to read CSV file'.format(str(e)))
        print('persons_tasks', persons_tasks)
        print('empty_fields', empty_fields)
