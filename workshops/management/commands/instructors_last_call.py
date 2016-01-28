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
            ttt = Tag.objects.get(name='TTT')
            instructor_badges = Badge.objects.instructor_badges()
            trainees = Task.objects.filter(event=event, role=learner).exclude(person__badges__in=instructor_badges)
        except ObjectDoesNotExist as e:
            self.stderr.write(str(e))
            sys.exit(1)

        # Report.
        people = list(set([(t.person.family, t.person.personal, t.person.email) for t in trainees]))
        people.sort()
        for (family, personal, email) in people:
            self.stdout.write('{0} {1} <{2}>'.format(personal, family, email))
