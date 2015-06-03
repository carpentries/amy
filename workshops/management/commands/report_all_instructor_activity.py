import sys
import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from workshops.models import Award, Badge, Person, Qualification, Role, Task


class Command(BaseCommand):
    args = ''
    help = 'Report all instructor activity.'

    instructor_role = Role.objects.get(name='instructor')
    helper_role = Role.objects.get(name='helper')

    def handle(self, *args, **options):
        if len(args) != 0:
            raise CommandError('Usage: report_all_instructor_activity')

        instructor_badge = Badge.objects.get(name='instructor')

        result = []
        all_awards = Award.objects.filter(badge=instructor_badge)
        for award in all_awards:
            person = award.person
            if not person.email:
                continue
            tasks = Task.objects.filter(person=person)\
                                .filter(Q(role=self.instructor_role) |
                                        Q(role=self.helper_role))
            tasks = [{'slug': t.event.slug,
                      'start': t.event.start,
                      'role': t.role.name,
                      'others': self.others(t.event, person)}
                     for t in tasks]
            can_teach = self.qualifications(person)
            record = {'name': person.get_full_name(),
                      'email': person.email,
                      'airport': person.airport.iata
                                 if person.airport
                                 else None,
                      'github': person.github,
                      'twitter': person.twitter,
                      'can_teach': can_teach,
                      'became_instructor': award.awarded,
                      'tasks': tasks}
            result.append(record)
        yaml.dump(result, stream=sys.stdout)

    def others(self, event, person):
        tasks = Task.objects.filter(event=event)\
                            .filter(Q(role=self.instructor_role) |
                                    Q(role=self.helper_role))\
                            .exclude(person=person)
        return [t.person.get_full_name() for t in tasks]

    def qualifications(self, person):
        return [q.skill.name for q in Qualification.objects.filter(person=person)]
