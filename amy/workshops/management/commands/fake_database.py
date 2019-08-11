import itertools
from datetime import timedelta
from random import (
    random,
    choice,
    uniform,
    sample as random_sample,
    randint,
)

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django_countries import countries as Countries
from faker import Faker
from faker.providers import BaseProvider

from extrequests.models import (
    DataAnalysisLevel,
    DataVariant,
    WorkshopInquiryRequest,
    SelfOrganizedSubmission,
)
from workshops.models import (
    Airport,
    Role,
    Tag,
    Badge,
    Lesson,
    Person,
    Award,
    Qualification,
    Organization,
    Event,
    Task,
    TrainingRequirement,
    TrainingProgress,
    TrainingRequest,
    KnowledgeDomain,
    Membership,
    AcademicLevel,
    ComputingExperienceLevel,
    Language,
    Curriculum,
    InfoSource,
    WorkshopRequest,
)
from workshops.util import create_username


def randbool(chances_of_true):
    return random() < chances_of_true


def sample(population, k=None):
    """Behaves like random.sample, but if k is omitted, it default to
    randint(1, len(population)), so that a non-empty sample is returned."""

    population = list(population)

    if k is None:
        k = randint(1, len(population))

    return random_sample(population, k)


class UniqueUrlProvider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.faker = Faker()
        self._generated_urls = set()

    def unique_url(self):
        while True:
            url = self.faker.url()
            if url not in self._generated_urls:
                break

        self._generated_urls.add(url)
        return url


class Command(BaseCommand):
    help = 'Add fake data to the database.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.faker = Faker()
        self.faker.add_provider(UniqueUrlProvider)

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed', action='store', default=None,
            help='Provide an initial seed for randomization mechanism.',
        )

    def fake_airports(self):
        """Add some airports."""
        # we're not doing anything here, since data migrations already add some
        # airports
        self.stdout.write('Generating 0 fake airports...')

    def fake_roles(self):
        """Provide fixed roles."""
        roles = [
            ('helper', 'Helper'),
            ('instructor', 'Instructor'),
            ('host', 'Workshop host'),
            ('learner', 'Learner'),
            ('organizer', 'Workshop organizer'),
            ('contributor', 'Contributed to lesson materials')
        ]
        
        self.stdout.write('Generating {} fake roles...'.format(len(roles)))

        for name, verbose_name in roles:
            Role.objects.get_or_create(
                name=name,
                defaults=dict(verbose_name=verbose_name)
            )

    def fake_groups(self):
        """Provide authentication groups."""
        groups = ['administrators', 'invoicing', 'steering committee',
                  'trainers']

        self.stdout.write(
            'Generating {} auth groups...'.format(len(groups)))

        for group in groups:
            Group.objects.get_or_create(name=group)

    def fake_tags(self):
        """Provide fixed tags. All other tags are pre-created through data
        migrations."""
        tags = [
            ('SWC', 'Software Carpentry Workshop'),
            ('DC', 'Data Carpentry Workshop'),
            ('LC', 'Library Carpentry Workshop'),
            ('WiSE', 'Women in Science and Engineering'),
            ('TTT', 'Train the Trainers'),
            ('online', 'Events taking place entirely online'),
            ('stalled', 'Events with lost contact with the host or TTT events'
                        ' that aren\'t running.'),
            ('unresponsive', 'Events whose hosts and/or organizers aren\'t '
                             'going to send attendance data'),
            ('hackathon', 'Event is a hackathon'),
            ('cancelled', 'Events that were supposed to happen but due to some'
                          ' circumstances got cancelled'),
            ('LSO', 'Lesson Specific Onboarding'),
            ('ITT', 'Instructor Trainer Training (Trainer Training)'),
            ('LMO', 'Lesson Maintainer Onboarding'),
        ]

        self.stdout.write('Generating {} fake tags...'.format(len(tags)))

        for tag, details in tags:
            Tag.objects.get_or_create(name=tag, defaults=dict(details=details))

    def fake_badges(self):
        """Provide fixed badges."""
        badges = [
            ('creator', 'Creator', 'Creating learning materials and other '
                                   'content'),
            ('swc-instructor', 'Software Carpentry Instructor',
             'Teaching at Software Carpentry workshops or online'),
            ('member', 'Member', 'Software Carpentry Foundation member'),
            ('organizer', 'Organizer', 'Organizing workshops and learning '
                                       'groups'),
            ('dc-instructor', 'Data Carpentry Instructor',
             'Teaching at Data Carpentry workshops or online'),
            ('maintainer', 'Maintainer', 'Maintainer of Software or Data '
             'Carpentry lesson'),
            ('trainer', 'Trainer', 'Teaching instructor training workshops'),
            ('mentor', 'Mentor', 'Mentor of Carpentry Instructors'),
            ('mentee', 'Mentee', 'Mentee in Carpentry Mentorship Program'),
            ('lc-instructor', 'Library Carpentry Instructor',
             'Teaching at Library Carpentry workshops or online'),
        ]

        self.stdout.write('Generating {} fake badges...'.format(len(badges)))

        for name, title, criteria in badges:
            Badge.objects.get_or_create(
                name=name, defaults=dict(title=title, criteria=criteria))

    def fake_instructors(self, count=30):
        self.stdout.write('Generating {} fake instructors...'.format(count))
        for _ in range(count):
            self.fake_person(is_instructor=True)

    def fake_trainers(self, count=10):
        self.stdout.write('Generating {} fake trainers...'.format(count))
        for _ in range(count):
            self.fake_person(is_instructor=True, is_trainer=True)

    def fake_admins(self, count=10):
        self.stdout.write('Generating {} fake admins...'.format(count))
        for _ in range(count):
            person = self.fake_person(is_instructor=randbool(0.5))
            person.groups.add(choice(Group.objects.all()))
            person.is_active = True
            person.set_password(person.username)
            person.save()

    def fake_trainees(self, count=30):
        self.stdout.write('Generating {} fake trainees (and their training '
                          'progresses and training requests)...'.format(count))
        for _ in range(count):
            p = self.fake_person(is_instructor=randbool(0.1))
            training = choice(Event.objects.ttt())
            Task.objects.create(person=p, event=training,
                                role=Role.objects.get(name='learner'))

            self.fake_training_request(p)
            self.fake_training_progresses(p, training)

    def fake_training_progresses(self, p, training):
        trainers = Person.objects.filter(award__badge__name='trainer')
        for r in TrainingRequirement.objects.all():
            if randbool(0.4):
                if 'Homework' in r.name and randbool(0.5):
                    state = 'n'
                else:
                    state = 'p' if randbool(0.95) else 'f'

                evaluated_by = None if state == 'n' else choice(trainers)
                event = training if r.name == 'Training' else None
                url = self.faker.url() if 'Homework' in r.name else None
                TrainingProgress.objects.create(
                    trainee=p,
                    requirement=r,
                    evaluated_by=evaluated_by,
                    state=state,
                    discarded=randbool(0.05),
                    event=event,
                    url=url,
                    notes='',
                )

    def fake_training_request(self, person_or_None):
        if person_or_None is None:
            state = 'p' if randbool(0.5) else 'd'
            person = self.fake_person(is_instructor=False)
        else:
            state = 'a'
            person = person_or_None

        occupation = choice(TrainingRequest._meta.get_field('occupation')
                                           .choices)[0]
        training_completion_agreement = randbool(0.5)
        underrepresented_choices = (
            TrainingRequest._meta.get_field('underrepresented').choices
        )
        req = TrainingRequest.objects.create(
            state=state,
            person=person_or_None,
            group_name=self.faker.city() if randbool(0.1) else '',
            personal=person.personal,
            middle='',
            family=person.family,
            email=person.email,
            github=person.github,
            occupation=occupation,
            occupation_other=self.faker.job() if occupation == '' else '',
            affiliation=person.affiliation,
            location=self.faker.city(),
            country=choice(Countries)[0],
            underresourced=randbool(0.6),
            domains_other='',
            underrepresented=choice(underrepresented_choices)[0],
            underrepresented_details=choice(
                ['', self.faker.paragraph(nb_sentences=1)]
            ),
            nonprofit_teaching_experience='',
            previous_training=choice(
                TrainingRequest.PREVIOUS_TRAINING_CHOICES)[0],
            previous_training_other='',
            previous_training_explanation=self.faker.text(),
            previous_experience=choice(
                TrainingRequest.PREVIOUS_EXPERIENCE_CHOICES)[0],
            previous_experience_other='',
            programming_language_usage_frequency=choice(
                TrainingRequest.PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES)[0],
            teaching_frequency_expectation=choice(
                TrainingRequest.TEACHING_FREQUENCY_EXPECTATION_CHOICES)[0],
            teaching_frequency_expectation_other='',
            max_travelling_frequency=choice(
                TrainingRequest.MAX_TRAVELLING_FREQUENCY_CHOICES)[0],
            max_travelling_frequency_other='',
            reason=self.faker.text(),
            training_completion_agreement=training_completion_agreement,
            workshop_teaching_agreement=randbool(0.5) if training_completion_agreement else False,
        )
        req.domains.set(sample(KnowledgeDomain.objects.all()))
        req.previous_involvement.set(sample(Role.objects.all()))

        if person_or_None is None:
            person.delete()

    def fake_person(self, *, is_instructor, is_trainer=False):
        airport = choice(Airport.objects.all())

        email = choice([self.faker.email(),
                        self.faker.safe_email(),
                        self.faker.free_email(),
                        self.faker.company_email()])

        gender = choice(Person.GENDER_CHOICES)[0]

        if gender == 'F':
            personal_name = self.faker.first_name_female()
            family_name = self.faker.last_name_female()
        elif gender == 'M':
            personal_name = self.faker.first_name_male()
            family_name = self.faker.last_name_male()
        else:
            personal_name = self.faker.first_name()
            family_name = self.faker.last_name()

        social_username = self.faker.user_name()

        if randbool(0.6):
            # automatically generate username
            username = create_username(personal_name, family_name)
        else:
            # assume that the username is provided by the person
            username = social_username

        github = social_username
        twitter = social_username
        url = self.faker.url() if randbool(0.5) else ''

        person = Person.objects.create(
            personal=personal_name,
            family=family_name,
            email=email,
            gender=gender,
            may_contact=randbool(0.5),
            publish_profile=randbool(0.5),
            airport=airport,
            twitter=twitter,
            github=github,
            url=url,
            username=username,
            country=choice(Countries)[0],
        )

        if is_instructor:
            # Add one or more instructor badges
            awards = []
            badges = sample(Badge.objects.instructor_badges())
            for badge in badges:
                date = self.faker.date_time_between(start_date='-5y').date()
                awards.append(Award(person=person, badge=badge, awarded=date))
            Award.objects.bulk_create(awards)

            if randbool(0.75):
                # Add one or more qualifications
                Qualification.objects.bulk_create(
                    Qualification(person=person, lesson=lesson)
                    for lesson in sample(Lesson.objects.all())
                )

        if is_trainer:
            date = self.faker.date_time_between(start_date='-5y').date()
            trainer = Badge.objects.get(name='trainer')
            Award.objects.create(person=person, badge=trainer, awarded=date)

        return person

    def fake_organizations(self, count=10):
        """Add some organizations that host events."""
        self.stdout.write('Generating {} fake organizations...'.format(count))

        for _ in range(count):
            Organization.objects.create(
                domain=self.faker.domain_name(),
                fullname=self.faker.company(),
                country=choice(Countries)[0],
            )

    def fake_memberships(self, count=10):
        self.stdout.write('Generating {} fake memberships...'.format(count))

        for _ in range(count):
            start = self.faker.date_time_between(start_date='-5y').date()
            Membership.objects.create(
                variant=choice(Membership.MEMBERSHIP_CHOICES)[0],
                agreement_start=start,
                agreement_end=start + timedelta(days=365),
                contribution_type=choice(Membership.CONTRIBUTION_CHOICES)[0],
                workshops_without_admin_fee_per_agreement=randint(5, 15),
                self_organized_workshops_per_agreement=randint(5, 15),
                organization=choice(Organization.objects.all()),
            )

    def fake_current_events(self, count=5, **kwargs):
        """Ongoing and upcoming events."""
        self.stdout.write('Generating {} fake current events...'.format(count))

        for _ in range(count):
            self.fake_event(future_date=True, **kwargs)

    def fake_unpublished_events(self, count=5):
        """Events with missing location data (which is required for publishing
        them)."""
        self.stdout.write(
            'Generating {} fake unpublished events...'.format(count))

        for _ in range(count):
            self.fake_event(location_data=False)

    def fake_self_organized_events(self, count=5):
        """Full-blown events with 'self-organized' host."""
        self.stdout.write(
            'Generating {} fake self organized events...'.format(count))

        for _ in range(count):
            e = self.fake_event(self_organized=True)
            e.invoice_status = choice(Event.INVOICED_CHOICES)[0]
            e.save()

    def fake_ttt_events(self, count=10):
        self.stdout.write(
            'Generating {} fake train-the-trainer events...'.format(count))

        for _ in range(count):
            e = self.fake_event()
            e.slug += '-ttt'
            e.tags.set([Tag.objects.get(name='TTT')])
            e.save()

    def fake_event(self, *, location_data=True, self_organized=False,
                   add_tags=True, future_date=False):
        if future_date:
            start = self.faker.date_time_between(start_date='now',
                                                 end_date='+120d').date()
        else:
            start = self.faker.date_time_between(start_date='-120d').date()
        city = self.faker.city().replace(' ', '-').lower()
        if self_organized:
            org = Organization.objects.get(domain='self-organized')
        else:
            org = choice(Organization.objects.exclude(domain='self-organized'))

        # The following line may result in IntegrityError from time to time,
        # because we don't guarantee that the url is unique. In that case,
        # simply create new database (rm db.sqlite3 && python manage.py migrate)
        # and rerun fake_database command (python manage.py fake_database). Be
        # aware that creating a database deletes all data in the existing
        # database!
        e = Event.objects.create(
            slug='{:%Y-%m-%d}-{}'.format(start, city),
            start=start,
            end=start + timedelta(days=2),
            url=self.faker.unique_url(),
            host=org,
            # needed in order for event to be published
            country=choice(Countries)[0] if location_data else None,
            venue=self.faker.word().title() if location_data else '',
            address=self.faker.street_address() if location_data else '',
            latitude=uniform(-90, 90) if location_data else None,
            longitude=uniform(0, 180) if location_data else None,
            metadata_changed=randbool(0.1),
        )
        if add_tags:
            e.tags.set(sample(Tag.objects.exclude(name='TTT'), 2))
        return e

    def fake_tasks(self, count=120):
        self.stdout.write('Generating {} fake tasks...'.format(count))

        events = Event.objects.all()
        persons = Person.objects.all()
        roles = Role.objects.all()
        all_possible = itertools.product(events, persons, roles)

        for event, person, role in sample(all_possible, count):
            Task.objects.create(
                event=event,
                person=person,
                role=role,
                title=(self.faker.sentence(nb_words=4, variable_nb_words=True)
                       if randbool(0.2) else ''),
                url=self.faker.url() if randbool(0.2) else '',
            )

    def fake_unmatched_training_requests(self, count=20):
        self.stdout.write('Generating {} fake unmatched '
                          'training requests...'.format(count))

        for _ in range(count):
            self.fake_training_request(None)

    def fake_duplicated_people(self, count=5):
        self.stdout.write('Generating {} fake '
                          'people duplications...'.format(count))

        for _ in range(count):
            p = Person.objects.order_by('?').first()
            p.id = None

            # avoid integrity errors due to unique constraints
            p.username = create_username(p.personal, p.family)
            p.twitter = None
            p.github = None
            p.email = self.faker.email()

            p.save()

    def fake_workshop_requests(self, count=10):
        self.stdout.write('Generating {} fake '
                          'workshop requests...'.format(count))

        curricula = Curriculum.objects.filter(active=True)
        organizations = Organization.objects.all()

        for _ in range(count):
            if randbool(0.5):
                language = Language.objects.get(subtag='en')
            else:
                language = choice(Language.objects.all())

            if randbool(0.3):
                org = choice(organizations)
                org_name = ''
                org_url = ''
            else:
                org = None
                org_name = self.faker.company()
                org_url = self.faker.url()

            public_event = choice(WorkshopRequest.PUBLIC_EVENT_CHOICES)[0]
            public_event_other = (
                self.faker.sentence() if public_event == 'other'
                else ""
            )
            administrative_fee = choice(WorkshopRequest.FEE_CHOICES)[0]
            scholarship_circumstances = (
                self.faker.sentence() if administrative_fee == 'waiver'
                else ""
            )
            travel_expences_management = choice(
                WorkshopRequest.TRAVEL_EXPENCES_MANAGEMENT_CHOICES)[0]
            travel_expences_management_other = (
                self.faker.sentence() if travel_expences_management == ''
                else ""
            )
            institution_restrictions = choice(
                WorkshopRequest.RESTRICTION_CHOICES)[0]
            institution_restrictions_other = (
                self.faker.sentence() if institution_restrictions == ''
                else ""
            )


            req = WorkshopRequest.objects.create(
                state=choice(['p', 'd', 'a']),
                data_privacy_agreement=randbool(0.5),
                code_of_conduct_agreement=randbool(0.5),
                host_responsibilities=randbool(0.5),

                personal=self.faker.first_name(),
                family=self.faker.last_name(),
                email=self.faker.email(),

                institution=org,
                institution_other_name=org_name,
                institution_other_URL=org_url,
                institution_department='',

                public_event=public_event,
                public_event_other=public_event_other,
                additional_contact=(
                    'Test Person <email@email.com>,'
                    'Another Person <person@example.com>'
                ),

                location=self.faker.city(),
                country=choice(Countries)[0],

                preferred_dates=self.faker.date_time_between(
                    start_date='now', end_date='+1y').date(),
                other_preferred_dates='Alternatively: soon',

                language=language,
                number_attendees=choice(
                    WorkshopRequest.ATTENDEES_NUMBER_CHOICES)[0],
                audience_description=self.faker.sentence(),

                administrative_fee=administrative_fee,
                scholarship_circumstances=scholarship_circumstances,
                travel_expences_agreement=True,
                travel_expences_management=travel_expences_management,
                travel_expences_management_other=travel_expences_management_other,

                institution_restrictions=institution_restrictions,
                institution_restrictions_other=institution_restrictions_other,

                carpentries_info_source_other='',
                user_notes = self.faker.sentence(),
            )

            req.requested_workshop_types.set(sample(curricula))
            req.carpentries_info_source.set(sample(InfoSource.objects.all()))
            req.save()

    def fake_workshop_inquiries(self, count=10):
        self.stdout.write('Generating {} fake '
                          'workshop inquiries...'.format(count))

        curricula = Curriculum.objects.filter(active=True)
        organizations = Organization.objects.all()

        for _ in range(count):
            if randbool(0.5):
                language = Language.objects.get(subtag='en')
            else:
                language = choice(Language.objects.all())

            if randbool(0.3):
                org = choice(organizations)
                org_name = ''
                org_url = ''
            else:
                org = None
                org_name = self.faker.company()
                org_url = self.faker.url()

            public_event = choice(
                WorkshopInquiryRequest.PUBLIC_EVENT_CHOICES)[0]
            public_event_other = (
                self.faker.sentence() if public_event == 'other'
                else ""
            )
            administrative_fee = choice(WorkshopInquiryRequest.FEE_CHOICES)[0]
            travel_expences_management = choice(
                WorkshopInquiryRequest.TRAVEL_EXPENCES_MANAGEMENT_CHOICES)[0]
            travel_expences_management_other = (
                self.faker.sentence() if travel_expences_management == ''
                else ""
            )
            institution_restrictions = choice(
                WorkshopInquiryRequest.RESTRICTION_CHOICES)[0]
            institution_restrictions_other = (
                self.faker.sentence() if institution_restrictions == ''
                else ""
            )

            req = WorkshopInquiryRequest.objects.create(
                state=choice(['p', 'd', 'a']),
                data_privacy_agreement=randbool(0.5),
                code_of_conduct_agreement=randbool(0.5),
                host_responsibilities=randbool(0.5),

                personal=self.faker.first_name(),
                family=self.faker.last_name(),
                email=self.faker.email(),

                institution=org,
                institution_other_name=org_name,
                institution_other_URL=org_url,
                institution_department='',

                public_event=public_event,
                public_event_other=public_event_other,
                additional_contact=(
                    'Test Person <email@email.com>,'
                    'Another Person <person@example.com>'
                ),

                location=self.faker.city(),
                country=choice(Countries)[0],

                routine_data_other='',
                domains_other='',

                audience_description=self.faker.sentence(),

                preferred_dates=self.faker.date_time_between(
                    start_date='now', end_date='+1y').date(),
                other_preferred_dates='Alternatively: soon',

                language=language,
                number_attendees=choice(
                    WorkshopInquiryRequest.ATTENDEES_NUMBER_CHOICES)[0],

                administrative_fee=administrative_fee,
                travel_expences_agreement=True,
                travel_expences_management=travel_expences_management,
                travel_expences_management_other=travel_expences_management_other,

                institution_restrictions=institution_restrictions,
                institution_restrictions_other=institution_restrictions_other,

                carpentries_info_source_other='',
                user_notes = self.faker.sentence(),
            )

            req.routine_data.set(sample(DataVariant.objects.all()))
            req.domains.set(sample(KnowledgeDomain.objects.all()))
            req.academic_levels.set(sample(AcademicLevel.objects.all()))
            req.computing_levels.set(sample(ComputingExperienceLevel.objects.all()))
            req.requested_workshop_types.set(sample(curricula))
            req.carpentries_info_source.set(sample(InfoSource.objects.all()))
            req.save()


    def fake_selforganized_submissions(self, count=10):
        self.stdout.write('Generating {} fake '
                          'self-organized submissions...'.format(count))

        curricula = Curriculum.objects.filter(active=True)
        organizations = Organization.objects.all()

        for _ in range(count):
            if randbool(0.5):
                language = Language.objects.get(subtag='en')
            else:
                language = choice(Language.objects.all())

            if randbool(0.3):
                org = choice(organizations)
                org_name = ''
                org_url = ''
            else:
                org = None
                org_name = self.faker.company()
                org_url = self.faker.url()

            public_event = choice(
                SelfOrganizedSubmission.PUBLIC_EVENT_CHOICES)[0]
            public_event_other = (
                self.faker.sentence() if public_event == 'other'
                else ""
            )
            workshop_format = choice(SelfOrganizedSubmission.FORMAT_CHOICES)[0]
            workshop_format_other = (
                self.faker.sentence() if workshop_format == ''
                else ""
            )
            if randbool(0.5):
                workshop_types = curricula.filter(mix_match=True)
                workshop_types_explain = "\n".join([
                    str(lesson) for lesson in Lesson.objects.order_by("?")[:10]
                ])
            else:
                workshop_types = sample(curricula)
                workshop_types_explain = ""

            req = SelfOrganizedSubmission.objects.create(
                state=choice(['p', 'd', 'a']),
                data_privacy_agreement=randbool(0.5),
                code_of_conduct_agreement=randbool(0.5),
                host_responsibilities=randbool(0.5),

                personal=self.faker.first_name(),
                family=self.faker.last_name(),
                email=self.faker.email(),

                institution=org,
                institution_other_name=org_name,
                institution_other_URL=org_url,
                institution_department='',

                public_event=public_event,
                public_event_other=public_event_other,
                additional_contact=(
                    'Test Person <email@email.com>,'
                    'Another Person <person@example.com>'
                ),

                workshop_url=self.faker.url(),
                workshop_format=workshop_format,
                workshop_format_other=workshop_format_other,
                workshop_types_other='',
                workshop_types_other_explain=workshop_types_explain,

                language=language,
            )

            req.workshop_types.set(workshop_types)
            req.save()

    def handle(self, *args, **options):
        seed = options['seed']
        if seed is not None:
            self.faker.seed(seed)

        try:
            self.fake_groups()
            self.fake_airports()
            self.fake_roles()
            self.fake_tags()
            self.fake_badges()
            self.fake_instructors()
            self.fake_trainers()
            self.fake_admins()
            self.fake_organizations()
            self.fake_memberships()
            self.fake_current_events()
            self.fake_unpublished_events()
            self.fake_self_organized_events()
            self.fake_ttt_events()
            self.fake_tasks()
            self.fake_trainees()
            self.fake_unmatched_training_requests()
            self.fake_duplicated_people()
            self.fake_workshop_requests()
            self.fake_workshop_inquiries()
            self.fake_selforganized_submissions()
        except IntegrityError as e:
            print("!!!" * 10)
            print("Delete the database, and rerun this script.")
            print("!!!" * 10)
            raise e
