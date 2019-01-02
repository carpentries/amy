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
from django_countries import countries as Countries
from faker import Faker
from faker.providers import BaseProvider

from extrequests.models import (
    ProfileUpdateRequest,
    EventRequest,
    EventSubmission,
    DCSelfOrganizedEventRequest,
    DCWorkshopDomain,
    DCWorkshopTopic,
    DataAnalysisLevel,
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
    InvoiceRequest,
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
        # we're not doing anything here, since:
        # 1. data migrations add some airports already
        # 2. we'll have more airports as fixtures as of #626
        pass

    def fake_roles(self):
        self.stdout.write('Generating fake roles...')
        roles = [
            ('helper', 'Helper'),
            ('instructor', 'Instructor'),
            ('host', 'Workshop host'),
            ('learner', 'Learner'),
            ('organizer', 'Workshop organizer'),
            ('contributor', 'Contributed to lesson materials')
        ]
        """Provide fixed roles (before they end up in fixtures, see #626)."""
        for name, verbose_name in roles:
            Role.objects.create(name=name, verbose_name=verbose_name)

    def fake_groups(self):
        # Two groups are already in the migrations: Administrator
        # and Steering Committee
        self.stdout.write('Generating fake groups...')
        Group.objects.create(name='invoicing')
        Group.objects.create(name='trainers')

    def fake_tags(self):
        """Provide fixed tags (before they end up in fixtures, see #626)."""
        self.stdout.write('Generating fake tags...')
        tags = [
            ('SWC', 'Software Carpentry Workshop'),
            ('DC', 'Data Carpentry Workshop'),
            ('LC', 'Library Carpentry Workshop'),
            ('WiSE', 'Women in Science and Engineering'),
            ('TTT', 'Train the Trainers'),
        ]
        for tag, details in tags:
            Tag.objects.create(name=tag, details=details)

    def fake_badges(self):
        """Provide fixed badges."""
        # Some badges are already in the migrations: swc-instructor,
        # dc-instructor, maintainer, trainer, lc-instructor.
        self.stdout.write('Generating fake badges...')
        badges = [
            ('creator', 'Creator',
             'Creating learning materials and other content'),
            ('member', 'Member', 'Software Carpentry Foundation member'),
            ('organizer', 'Organizer',
             'Organizing workshops and learning groups'),
        ]
        for name, title, criteria in badges:
            Badge.objects.create(name=name, title=title, criteria=criteria)

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
        self.stdout.write('Generating {} fake trainees '
                          '(and their training progresses '
                          'as well as training requests)...'.format(count))
        for _ in range(count):
            p = self.fake_person(is_instructor=randbool(0.1))
            training = choice(Event.objects.ttt())
            Task.objects.create(person=p, event=training,
                                role=Role.objects.get(name='learner'))

            self.fake_training_progresses(p, training)
            if randbool(0.8):
                self.fake_training_request(p)

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

        occupation = choice(ProfileUpdateRequest.OCCUPATION_CHOICES)[0]
        training_completion_agreement = randbool(0.5)
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
            underrepresented=randbool(0.6),
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
            comment=self.faker.text() if randbool(0.3) else '',
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

        github = social_username if randbool(0.5) else None
        twitter = social_username if randbool(0.5) else None
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
            self.fake_event(**kwargs)

    def fake_uninvoiced_events(self, count=5):
        """Preferably in the past, and with 'uninvoiced' status."""
        self.stdout.write(
            'Generating {} fake uninvoiced events...'.format(count))

        for _ in range(count):
            e = self.fake_event()
            e.invoice_status = 'not-invoiced'
            e.save()

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
                   add_tags=True):
        start = self.faker.date_time_between(start_date='-5y').date()
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

        for _ in range(count):
            if randbool(0.5):
                language = Language.objects.get(subtag='en')
            else:
                language = choice(Language.objects.all())

            req = EventRequest.objects.create(
                name=self.faker.name(),
                email=self.faker.email(),
                affiliation=self.faker.company(),
                location=self.faker.city(),
                country=choice(Countries)[0],
                conference='',
                preferred_date=str(self.faker.date_time_between(
                    start_date='now', end_date='+1y').date()),
                language=language,
                workshop_type=choice(EventRequest.WORKSHOP_TYPE_CHOICES)[0],
                approx_attendees=choice(
                    EventRequest.ATTENDEES_NUMBER_CHOICES)[0],
                attendee_domains_other='',
                data_types=choice(EventRequest.DATA_TYPES_CHOICES)[0],
                understand_admin_fee=True,
                admin_fee_payment=choice(
                    EventRequest.ADMIN_FEE_PAYMENT_CHOICES)[0],
                fee_waiver_request=randbool(0.2),
                cover_travel_accomodation=randbool(0.6),
                travel_reimbursement=choice(
                    EventRequest.TRAVEL_REIMBURSEMENT_CHOICES)[0],
                travel_reimbursement_other='',
                comment='',
            )
            req.attendee_domains.set(sample(KnowledgeDomain.objects.all()))
            req.attendee_academic_levels.set(sample(
                AcademicLevel.objects.all()))
            req.attendee_computing_levels.set(sample(
                ComputingExperienceLevel.objects.all()))
            req.attendee_data_analysis_level.set(sample(
                DataAnalysisLevel.objects.all()))
            req.save()

    def fake_workshop_submissions(self, count=10):
        self.stdout.write('Generating {} fake '
                          'workshop submissions...'.format(count))

        for _ in range(count):
            EventSubmission.objects.create(
                url=self.faker.url(),
                contact_name=self.faker.name(),
                contact_email=self.faker.email(),
                self_organized=randbool(0.5),
                notes='',
            )

    def fake_dc_selforganized_workshop_requests(self, count=5):
        self.stdout.write('Generating {} fake dc self-organized '
                          'workshops requests...'.format(count))

        for _ in range(count):
            date = self.faker.date_time_between(start_date='now',
                                                end_date='+1y')

            req = DCSelfOrganizedEventRequest.objects.create(
                name=self.faker.name(),
                email=self.faker.email(),
                organization=self.faker.company(),
                instructor_status=choice(
                    DCSelfOrganizedEventRequest.INSTRUCTOR_CHOICES)[0],
                is_partner=choice(
                    DCSelfOrganizedEventRequest.PARTNER_CHOICES)[0],
                is_partner_other='',
                location=self.faker.city(),
                country=choice(Countries)[0],
                associated_conference='',
                dates=str(date.date()),
                domains_other='',
                topics_other='',
                payment=choice(DCSelfOrganizedEventRequest.PAYMENT_CHOICES)[0],
                fee_waiver_reason='',
                handle_registration=True,
                distribute_surveys=True,
                follow_code_of_conduct=True,
            )
            req.domains.set(sample(DCWorkshopDomain.objects.all()))
            req.topics.set(sample(DCWorkshopTopic.objects.all()))
            req.attendee_academic_levels.set(sample(
                AcademicLevel.objects.all()))
            req.attendee_data_analysis_level.set(sample(
                DataAnalysisLevel.objects.all()))

    def fake_profile_update_requests(self, count=20):
        self.stdout.write('Generating {} fake '
                          'profile update requests...'.format(count))

        for _ in range(count):
            p = Person.objects.order_by('?').first()  # type: Person
            req = ProfileUpdateRequest.objects.create(
                active=randbool(0.5),
                personal=(p.personal if randbool(0.9)
                          else self.faker.first_name()),
                middle=p.middle,
                family=p.family if randbool(0.9) else self.faker.last_name(),
                email=p.email if randbool(0.8) else self.faker.email(),
                affiliation=(p.affiliation if randbool(0.8)
                             else self.faker.company()),
                airport_iata=(p.airport.iata
                              if randbool(0.9) and p.airport is not None
                              else choice(Airport.objects.all()).iata),
                occupation=choice(ProfileUpdateRequest.OCCUPATION_CHOICES)[0],
                occupation_other='',
                github=p.github or '',
                twitter=p.twitter or '',
                orcid=p.orcid or '',
                website=p.url or '',
                gender=choice(ProfileUpdateRequest.GENDER_CHOICES)[0],
                gender_other='',
                domains_other='',
                lessons_other='',
                notes='',
            )
            req.domains.set(p.domains.all() if randbool(0.9) else
                            sample(KnowledgeDomain.objects.all()))
            req.languages.set(p.languages.all() if randbool(0.9) else
                              sample(Language.objects.all()))
            req.lessons.set(p.lessons.all() if randbool(0.9) else
                            sample(Lesson.objects.all()))

    def fake_invoice_requests(self, count=10):
        self.stdout.write('Generating {} fake '
                          'invoice requests...'.format(count))

        for _ in range(count):
            status = choice(InvoiceRequest.STATUS_CHOICES)[0]
            sent_date = (None if status == 'not-invoiced' else
                         self.faker.date_time_between(start_date='-1y').date())
            paid_date = (
                self.faker.date_time_between(start_date=sent_date).date()
                if status == 'paid' else None)
            org = Organization.objects.order_by('?').first()
            event = (Event.objects.order_by('?').first()
                     if randbool(0.8) else None)

            req = InvoiceRequest.objects.create(
                status=status,
                sent_date=sent_date,
                paid_date=paid_date,
                organization=org,
                reason=choice(InvoiceRequest.INVOICE_REASON)[0],
                reason_other='',
                date=(self.faker.date_time_between(start_date='-1y').date()
                      if sent_date is None else sent_date),
                event=event,
                event_location='',
                item_id='',
                postal_number='',
                contact_name=org.fullname,
                contact_email=self.faker.email(),
                contact_phone='',
                full_address=self.faker.address(),
                amount=choice([1000, 2000, 10000]),
                currency=choice(InvoiceRequest.CURRENCY)[0],
                currency_other='',
                breakdown='',
                vendor_form_required=choice(InvoiceRequest.VENDOR_FORM_CHOICES)[0],
                vendor_form_link='',
                form_W9=randbool(0.5),
                receipts_sent=choice(InvoiceRequest.RECEIPTS_CHOICES)[0],
                shared_receipts_link='',
                notes='',
            )

    def handle(self, *args, **options):
        seed = options['seed']
        if seed is not None:
            self.faker.seed(seed)

        self.fake_airports()
        self.fake_roles()
        self.fake_groups()
        self.fake_tags()
        self.fake_badges()
        self.fake_instructors()
        self.fake_trainers()
        self.fake_admins()
        self.fake_organizations()
        self.fake_memberships()
        self.fake_current_events()
        self.fake_uninvoiced_events()
        self.fake_unpublished_events()
        self.fake_self_organized_events()
        self.fake_ttt_events()
        self.fake_tasks()
        self.fake_trainees()
        self.fake_unmatched_training_requests()
        self.fake_duplicated_people()
        self.fake_workshop_requests()
        self.fake_workshop_submissions()
        self.fake_dc_selforganized_workshop_requests()
        self.fake_profile_update_requests()
        self.fake_invoice_requests()
