from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from workshops.util import \
    upload_person_task_csv, \
    verify_upload_person_task, \
    create_uploaded_persons_tasks

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

        errors = verify_upload_person_task(persons_tasks)
        if errors:
            raise CommandError('Errors in upload:\n{0}'.format('\n'.join(errors)))

        try:
            persons, tasks = create_uploaded_persons_tasks(persons_tasks)
        except (IntegrityError, ObjectDoesNotExist) as e:
            raise CommandError('Failed to create persons/tasks: {0}'.format(str(e)))

        for p in persons:
            print(p)
        for t in tasks:
            print(t)
