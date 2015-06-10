import datetime
from django.core.management.base import BaseCommand, CommandError
from workshops.models import Award, Badge, Event, Tag, Task


class Command(BaseCommand):
    args = 'since'
    help = 'Report people who have done instructor training since date but do not have badges.'

    def handle(self, *args, **options):

        # Setup.
        today = datetime.date.today()
        if len(args) == 0:
            since = today - datetime.timedelta(days=365)
        elif len(args) == 1:
            since = datetime.date(*[int(x) for x in args[0].split('-')])
        else:
            raise CommandError('Usage: report_incomplete_instructors [since]')

        # Construct {person:date} dictionary of everyone who's done instructor training
        # in the past.
        training_tag = Tag.objects.get(name='TTT')
        training_events = Event.objects.filter(tags=training_tag).filter(end__lte=today)
        training_tasks = Task.objects.filter(event__in=training_events).order_by('event__start')
        training_tasks = dict([(tt.person, tt.event.start) for tt in training_tasks
                               if tt.event.start >= since])

        # Subtract people who have badges.
        instructor_badge = Badge.objects.get(name='instructor')
        instructor_awards = Award.objects.filter(badge=instructor_badge)
        for ia in instructor_awards:
            if ia.person in training_tasks:
                del training_tasks[ia.person]

        # Report.
        pairs = list(training_tasks.items())
        pairs.sort(key=lambda x: (x[1], x[0].family, x[0].personal))
        pairs.reverse()
        for (name, date) in pairs:
            print(date, name)
