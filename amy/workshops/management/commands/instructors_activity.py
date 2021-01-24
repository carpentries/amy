import os
import logging

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import get_template

from workshops.models import Badge, Person, Role

logger = logging.getLogger()


class Command(BaseCommand):
    help = 'Report instructors activity.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-out-for-real', action='store_true', default=False,
            help='Send information to the instructors.',
        )
        parser.add_argument(
            '--no-may-contact-only', action='store_true', default=False,
            help='Include instructors not willing to be contacted.',
        )
        parser.add_argument(
            '--django-mailing', action='store_true', default=False,
            help='Use Django mailing system. This requires some environmental '
                 'variables to be set, see `settings.py`.',
        )
        parser.add_argument(
            '-s', '--sender', action='store',
            default='workshops@carpentries.org',
            help='E-mail used in "from:" field.',
        )

    def foreign_tasks(self, tasks, person, roles):
        """List of other instructors' tasks, per event."""
        return [
            task.event.task_set.filter(role__in=roles)
                               .exclude(person=person)
                               .select_related('person')
            for task in tasks
        ]

    def fetch_activity(self, may_contact_only=True):
        roles = Role.objects.filter(name__in=['instructor', 'helper'])
        instructor_badges = Badge.objects.instructor_badges()

        instructors = Person.objects.filter(badges__in=instructor_badges)
        instructors = instructors.exclude(email__isnull=True)
        if may_contact_only:
            instructors = instructors.exclude(may_contact=False)

        # let's get some things faster
        instructors = instructors.select_related('airport') \
                                 .prefetch_related('task_set', 'lessons',
                                                   'award_set', 'badges')

        # don't repeat the records
        instructors = instructors.distinct()

        result = []
        for person in instructors:
            tasks = person.task_set.filter(role__in=roles) \
                                   .select_related('event', 'role')
            record = {
                'person': person,
                'lessons': person.lessons.all(),
                'instructor_awards': person.award_set.filter(
                    badge__in=person.badges.instructor_badges()
                ),
                'tasks': zip(tasks,
                             self.foreign_tasks(tasks, person, roles)),
            }
            result.append(record)

        return result

    def make_message(self, record):
        tmplt = get_template('mailing/instructor_activity.txt')
        return tmplt.render(context=record)

    def subject(self, record):
        # in future we can vary the subject depending on the record details
        return 'Updating your Software Carpentry information'

    def recipient(self, record):
        return record['person'].email

    def send_message(self, subject, message, sender, recipient, for_real=False,
                     django_mailing=False):
        if for_real:
            if django_mailing:
                send_mail(subject, message, sender, [recipient])

            else:
                command = 'mail -s "{subject}" -r {sender} {recipient}'.format(
                    subject=subject,
                    sender=sender,
                    recipient=recipient,
                )

                writer = os.popen(command, 'w')
                writer.write(message)
                writer.close()

        if self.verbosity >= 2:
            # write only a header
            self.stdout.write('-' * 40 + '\n')
            self.stdout.write('To: {}\n'.format(recipient))
            self.stdout.write('Subject: {}\n'.format(subject))
            self.stdout.write('From: {}\n'.format(sender))
        if self.verbosity >= 3:
            # write whole message out
            self.stdout.write(message + '\n')

    def handle(self, *args, **options):
        # default is dummy run - only actually send mail if told to
        send_for_real = options['send_out_for_real']

        # by default include only instructors who have `may_contact==True`
        no_may_contact_only = options['no_may_contact_only']

        # use mailing options from settings.py or the `mail` system command?
        django_mailing = options['django_mailing']

        # verbosity option is added by Django
        self.verbosity = int(options['verbosity'])

        sender = options['sender']

        results = self.fetch_activity(not no_may_contact_only)

        for result in results:
            message = self.make_message(result)
            subject = self.subject(result)
            recipient = self.recipient(result)
            self.send_message(subject, message, sender, recipient,
                              for_real=send_for_real,
                              django_mailing=django_mailing)

        if self.verbosity >= 1:
            self.stdout.write('Sent {} emails.\n'.format(len(results)))
