from datetime import timedelta
import itertools
import random

from django.core.management.base import BaseCommand
from django_countries import countries as Countries
from faker import Faker

from workshops.models import (
    Airport,
    Role,
    Tag,
    Badge,
    Lesson,
    Person,
    Award,
    Qualification,
    Host,
    Event,
    Task,
)


class Command(BaseCommand):
    help = 'Add fake data to the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed', action='store', default=None,
            help='Provide an initial seed for randomization mechanism.',
        )

    def fake_airports(self, faker, count=5):
        """Add some airports."""
        # we're not doing anything here, since:
        # 1. data migrations add some airports already
        # 2. we'll have more airports as fixtures as of #626
        pass

    def fake_roles(self, faker):
        """Provide fixed roles (before they end up in fixtures, see #626)."""
        roles = ['helper', 'instructor', 'host', 'learner', 'organizer',
                 'tutor', 'debriefed']
        for role in roles:
            Role.objects.create(name=role)

    def fake_tags(self, faker):
        """Provide fixed tags (before they end up in fixtures, see #626)."""
        tags = [
            ('SWC', 'Software Carpentry Workshop'),
            ('DC', 'Data Carpentry Workshop'),
            ('LC', 'Library Carpentry Workshop'),
            ('WiSE', 'Women in Science and Engineering'),
            ('TTT', 'Train the Trainers'),
        ]
        for tag, details in tags:
            Tag.objects.create(name=tag, details=details)

    def fake_badges(self, faker):
        """Provide fixed badges (before they end up in fixtures, see #626)."""
        # 4 badges are already in the migrations: swc-instructor,
        # dc-instructor, maintainer, and trainer
        badges = [
            ('creator', 'Creator',
             'Creating learning materials and other content'),
            ('member', 'Member', 'Software Carpentry Foundation member'),
            ('organizer', 'Organizer',
             'Organizing workshops and learning groups'),
        ]
        for name, title, criteria in badges:
            Badge.objects.create(name=name, title=title, criteria=criteria)

    def fake_instructors(self, faker, count=5, add_badge=True,
                         add_qualifications=True):
        """Add a few people with random instructor badge, random airport, and
        random qualification."""
        airports = list(Airport.objects.all())
        badges = list(Badge.objects.instructor_badges())
        lessons = list(Lesson.objects.all())
        for i in range(count):
            user_name = faker.user_name()
            emails = [faker.email(), faker.safe_email(), faker.free_email(),
                      faker.company_email()]
            gender = random.choice(Person.GENDER_CHOICES)[0]
            if gender == 'F':
                name = faker.first_name_female()
                last_name = faker.last_name_female()
            elif gender == 'M':
                name = faker.first_name_male()
                last_name = faker.last_name_male()
            else:
                name, last_name = faker.first_name(), faker.last_name()

            person = Person.objects.create(
                personal=name,
                middle=None,
                family=last_name,
                email=random.choice(emails),
                gender=gender,
                may_contact=random.choice([True, False]),
                airport=random.choice(airports),
                github=user_name,
                twitter=user_name,
                url=faker.url(),
                username=user_name,
            )

            if add_badge:
                Award.objects.create(
                    person=person, badge=random.choice(badges),
                    awarded=faker.date_time_this_year(before_now=True,
                                                      after_now=False).date(),
                )
            if add_qualifications:
                for lesson in random.sample(lessons, 4):
                    Qualification.objects.create(person=person, lesson=lesson)

    def fake_noninstructors(self, faker, count=5):
        """Add a few people who aren't instructors."""
        return self.fake_instructors(
            faker=faker, count=count, add_badge=False,
            add_qualifications=False,
        )

    def fake_hosts(self, faker, count=5):
        """Add some hosts for events."""
        countries = list(Countries)
        for i in range(count):
            Host.objects.create(
                domain=faker.domain_name(),
                fullname=faker.company(),
                country=random.choice(countries)[0],
            )

    def fake_current_events(self, faker, count=5):
        """Ongoing and upcoming events."""
        twodays = timedelta(days=2)
        hosts = list(Host.objects.exclude(domain='self-organized'))
        countries = list(Countries)

        for i in range(count):
            start = faker.date_time_this_year(before_now=False,
                                              after_now=True).date()
            Event.objects.create(
                slug='{:%Y-%m-%d}-{}'.format(start, faker.slug()),
                start=start,
                end=start + twodays,
                url=faker.url(),
                host=random.choice(hosts),
                # needed in order for event to be published
                country=random.choice(countries)[0],
                venue=faker.word().title(),
                address=faker.sentence(nb_words=4, variable_nb_words=True),
                latitude=random.uniform(-90, 90),
                longitude=random.uniform(0, 180),
            )

    def fake_uninvoiced_events(self, faker, count=5):
        """Preferably in the past, and with 'uninvoiced' status."""
        twodays = timedelta(days=2)
        countries = list(Countries)
        hosts = list(Host.objects.exclude(domain='self-organized'))

        for i in range(count):
            start = faker.date_time_this_year(before_now=True,
                                              after_now=False).date()
            Event.objects.create(
                slug='{:%Y-%m-%d}-{}'.format(start, faker.slug()),
                start=start,
                end=start + twodays,
                url=faker.url(),
                host=random.choice(hosts),
                # needed in order for event to be published
                country=random.choice(countries)[0],
                venue=faker.word().title(),
                address=faker.sentence(nb_words=4, variable_nb_words=True),
                latitude=random.uniform(-90, 90),
                longitude=random.uniform(0, 180),
                # needed in order for event to be uninvoiced
                invoice_status='not-invoiced',
            )

    def fake_unpublished_events(self, faker, count=5):
        """Events with missing location data (which is required for publishing
        them)."""
        twodays = timedelta(days=2)
        hosts = list(Host.objects.exclude(domain='self-organized'))

        for i in range(count):
            start = faker.date_time_this_year(before_now=True,
                                              after_now=True).date()
            Event.objects.create(
                slug='{:%Y-%m-%d}-{}'.format(start, faker.slug()),
                start=start,
                end=start + twodays,
                url=faker.url(),
                host=random.choice(hosts),
            )

    def fake_self_organized_events(self, faker, count=5):
        """Full-blown events with 'self-organized' host."""
        twodays = timedelta(days=2)
        self_organized = Host.objects.get(domain='self-organized')
        countries = list(Countries)
        invoice_statuses = Event.INVOICED_CHOICES

        for i in range(count):
            start = faker.date_time_this_year(before_now=True,
                                              after_now=True).date()
            Event.objects.create(
                slug='{:%Y-%m-%d}-{}'.format(start, faker.slug()),
                start=start,
                end=start + twodays,
                url=faker.url(),
                host=self_organized,
                # needed in order for event to be published
                country=random.choice(countries)[0],
                venue=faker.word().title(),
                address=faker.sentence(nb_words=4, variable_nb_words=True),
                latitude=random.uniform(-90, 90),
                longitude=random.uniform(0, 180),
                # needed in order for event to be uninvoiced
                invoice_status=random.choice(invoice_statuses)[0],
            )

    def fake_tasks(self, faker, count=50):
        events = Event.objects.all()
        persons = Person.objects.all()
        roles = Role.objects.all()
        all_possible = itertools.product(events, persons, roles)

        for event, person, role in random.sample(list(all_possible), count):
            Task.objects.create(event=event, person=person, role=role)

    def handle(self, *args, **options):
        faker = Faker()

        seed = options['seed']
        if seed is not None:
            faker.seed(seed)

        self.fake_airports(faker)
        self.fake_roles(faker)
        self.fake_tags(faker)
        self.fake_badges(faker)
        self.fake_instructors(faker)
        self.fake_noninstructors(faker)
        self.fake_hosts(faker)
        self.fake_current_events(faker)
        self.fake_uninvoiced_events(faker)
        self.fake_unpublished_events(faker)
        self.fake_self_organized_events(faker)
        self.fake_tasks(faker)
