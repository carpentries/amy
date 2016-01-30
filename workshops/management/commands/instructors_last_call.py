import sys
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from workshops.models import Badge, Event, Person, Role, Tag, Task

class Command(BaseCommand):
    help = 'Create mail addresses for events about to go stale: command line is event slugs.'

    def add_arguments(self, parser):
        parser.add_argument(
            'event', help='Event slug',
        )

    def handle(self, *args, **options):

        # Every learner who was at this event but isn't an instructor.
        try:
            slug = options['event']
            event = Event.objects.get(slug=slug)
            learner = Role.objects.get(name='learner')
            instructor_badges = Badge.objects.instructor_badges()
        except ObjectDoesNotExist as e:
            self.stderr.write(str(e))
            sys.exit(1)

        # Report.
        trainees = Person.objects\
                         .filter(task__event=event, task__role=learner)\
                         .exclude(badges__in=instructor_badges)\
                         .distinct()\
                         .order_by('family', 'personal', 'email')
        people = trainees.values_list('family', 'personal', 'email')            
        for (family, personal, email) in people:
            self.stdout.write('{0} {1} <{2}>'.format(personal, family, email))
