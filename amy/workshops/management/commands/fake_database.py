from datetime import timedelta
import itertools
from random import choice, randint, random
from random import sample as random_sample
from random import uniform
from typing import Any, List, Sequence

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import IntegrityError, transaction
from django.utils import timezone
from django_countries import countries as Countries
from faker import Faker
from faker.providers import BaseProvider

from consents.models import Consent, Term
from extrequests.models import (
    DataVariant,
    SelfOrganisedSubmission,
    WorkshopInquiryRequest,
)
from fiscal.models import Consortium, MembershipPersonRole, Partnership
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from trainings.models import Involvement
from workshops.models import (
    AcademicLevel,
    Airport,
    Award,
    Badge,
    ComputingExperienceLevel,
    Curriculum,
    Event,
    InfoSource,
    KnowledgeDomain,
    Language,
    Lesson,
    Member,
    MemberRole,
    Membership,
    Organization,
    Person,
    Qualification,
    Role,
    Tag,
    Task,
    TrainingProgress,
    TrainingRequest,
    TrainingRequirement,
    WorkshopRequest,
)
from workshops.utils.usernames import create_username


def randbool(chances_of_true: float) -> bool:
    return random() < chances_of_true


def sample[_T](population: Sequence[_T], k: int | None = None) -> list[_T]:
    """Behaves like random.sample, but if k is omitted, it default to
    randint(1, len(population)), so that a non-empty sample is returned."""

    population = list(population)

    if k is None:
        k = randint(1, len(population))

    return random_sample(population, k)


class UniqueUrlProvider(BaseProvider):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.faker = Faker()
        self._generated_urls: set[str] = set()

    def unique_url(self) -> str:
        while True:
            url = self.faker.url()
            if url not in self._generated_urls:
                break

        self._generated_urls.add(url)
        return url


class Command(BaseCommand):
    help = "Add fake data to the database."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.faker = Faker()
        self.faker.add_provider(UniqueUrlProvider)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--seed",
            action="store",
            default=None,
            help="Provide an initial seed for randomization mechanism.",
        )

    def fake_airports(self) -> None:
        """Add some airports."""
        # we're not doing anything here, since data migrations already add some
        # airports
        self.stdout.write("Generating 0 fake airports...")

    def fake_roles(self) -> None:
        """Provide fixed roles."""
        roles = [
            ("helper", "Helper"),
            ("instructor", "Instructor"),
            ("host", "Workshop host"),
            ("learner", "Learner"),
            ("organizer", "Workshop organizer"),
            ("contributor", "Contributed to lesson materials"),
        ]

        self.stdout.write("Generating {} fake roles...".format(len(roles)))

        for name, verbose_name in roles:
            Role.objects.get_or_create(name=name, defaults=dict(verbose_name=verbose_name))

    def fake_groups(self) -> None:
        """Provide authentication groups."""
        groups = ["administrators", "invoicing", "steering committee", "trainers"]

        self.stdout.write("Generating {} auth groups...".format(len(groups)))

        for group in groups:
            Group.objects.get_or_create(name=group)

    def fake_tags(self) -> None:
        """Provide fixed tags. All other tags are pre-created through data
        migrations."""
        tags = [
            ("automated-email", 10, "For the pilot run of email automation project"),
            ("DC", 20, "Data Carpentry Workshop"),
            ("LC", 30, "Library Carpentry Workshop"),
            ("SWC", 40, "Software Carpentry Workshop"),
            ("Circuits", 50, "Events with only partial Carpentries curriculum"),
            ("online", 60, "Events taking place entirely online"),
            ("TTT", 70, "Train the Trainers"),
            ("ITT", 80, "Instructor Trainer Training (Trainer Training)"),
            ("Pilot", 90, "To use for pilots of new or revamped curricula"),
            (
                "for-profit",
                100,
                "Corporate or for-profit institutions that may be paying higher fees",
            ),
            (
                "scholarship",
                110,
                "Events that have been granted a scholarship and have fees waived",
            ),
            (
                "private-event",
                120,
                "Workshops with this tag will not be displayed in our feeds and websites",
            ),
            (
                "cancelled",
                130,
                "Events that were supposed to happen but due to some circumstances got cancelled",
            ),
            (
                "unresponsive",
                140,
                "Events whose hosts and/or organizers aren't going to send attendance data",
            ),
            (
                "stalled",
                150,
                "Events with lost contact with the host or TTT events that aren't running.",
            ),
            ("LMO", 160, "Lesson Maintainer Onboarding"),
            ("LSO", 170, "Lesson Specific Onboarding"),
            ("hackathon", 180, "Event is a hackathon"),
            ("WiSE", 190, "Women in Science and Engineering"),
        ]

        self.stdout.write("Generating {} fake tags...".format(len(tags)))

        for tag, priority, details in tags:
            Tag.objects.get_or_create(name=tag, defaults=dict(priority=priority, details=details))

    def fake_instructors(self, count: int = 30) -> None:
        self.stdout.write("Generating {} fake instructors...".format(count))
        for _ in range(count):
            try:
                with transaction.atomic():
                    self.fake_person(is_instructor=True)
            except IntegrityError as e:
                print(f"Error generating fake person: {e}")

    def fake_trainers(self, count: int = 10) -> None:
        self.stdout.write("Generating {} fake trainers...".format(count))
        for _ in range(count):
            try:
                with transaction.atomic():
                    self.fake_person(is_instructor=True, is_trainer=True)
            except IntegrityError as e:
                print(f"Error generating fake person: {e}")

    def fake_admins(self, count: int = 10) -> None:
        self.stdout.write("Generating {} fake admins...".format(count))
        for _ in range(count):
            try:
                with transaction.atomic():
                    person = self.fake_person(is_instructor=randbool(0.5))
                    person.groups.add(choice(Group.objects.all()))
                    person.is_active = True
                    person.set_password(person.username)
                    person.save()
            except IntegrityError as e:
                print(f"Error generating fake person: {e}")

    def fake_trainees(self, count: int = 30) -> None:
        self.stdout.write(
            "Generating {} fake trainees (and their training progresses and training requests)...".format(count)
        )
        for _ in range(count):
            try:
                with transaction.atomic():
                    p = self.fake_person(is_instructor=randbool(0.1))
                    training = choice(Event.objects.ttt())
                    Task.objects.create(person=p, event=training, role=Role.objects.get(name="learner"))

                    self.fake_training_request(p)
                    self.fake_training_progresses(p, training)
            except IntegrityError as e:
                print(f"Error generating fake trainees: {e}")

    def fake_training_progresses(self, person: Person, training: Event) -> None:
        for requirement in TrainingRequirement.objects.all():
            if randbool(0.4):
                notes = ""
                if "Get Involved" in requirement.name and randbool(0.5):
                    state = "n"
                else:
                    if randbool(0.90):
                        state = "p"
                    elif randbool(0.50):
                        state = "a"
                    else:
                        state = "f"
                        notes += "Failed"

                event = training if requirement.name == "Training" else None
                if requirement.involvement_required:
                    involvement_type = choice(Involvement.objects.all())
                    date = (
                        self.faker.date_time_between(start_date="-5y").date()
                        if involvement_type.date_required
                        else None
                    )
                    url = self.faker.url() if involvement_type.url_required else None
                    trainee_notes = self.faker.sentence() if involvement_type.notes_required and randbool(0.5) else ""
                    notes += self.faker.sentence() if involvement_type.notes_required and not trainee_notes else ""
                else:
                    involvement_type = None
                    date = None
                    url = self.faker.url() if requirement.url_required else None
                    trainee_notes = ""

                TrainingProgress.objects.create(
                    trainee=person,
                    requirement=requirement,
                    involvement_type=involvement_type,
                    state=state,
                    event=event,
                    url=url,
                    date=date,
                    trainee_notes=trainee_notes,
                    notes=notes,
                )

    def fake_training_request(self, person_or_None: Person | None) -> None:
        if person_or_None is None:
            state = "p" if randbool(0.5) else "d"
            try:
                with transaction.atomic():
                    person = self.fake_person(is_instructor=False)
            except IntegrityError as e:
                print(f"Error generating fake training request: {e}")
                return
        else:
            state = "a"
            person = person_or_None

        # registration code
        # default (empty code) is used 25% of the time
        registration_code = ""
        override_invalid_code = False
        if randbool(0.5):
            # 50% of the time, use an existing code
            registration_code = choice(Membership.objects.all()).registration_code or ""
        elif randbool(0.5):
            # 25% of the time, use an invalid code and the override
            registration_code = self.faker.city()
            override_invalid_code = True

        occupation = choice(TrainingRequest.OCCUPATION_CHOICES)[0]
        underrepresented_choices = TrainingRequest.UNDERREPRESENTED_CHOICES
        eventbrite_url = ""
        if registration_code and randbool(0.5):
            eventbrite_url = "https://eventbrite.com/fake-" f"{self.faker.random_number(digits=12, fix_len=True)}"
        req = TrainingRequest.objects.create(
            state=state,
            person=person_or_None,
            review_process="preapproved" if registration_code else "open",
            member_code=registration_code,
            member_code_override=override_invalid_code,
            eventbrite_url=eventbrite_url,
            personal=person.personal,
            middle="",
            family=person.family,
            email=person.email or "",
            github=person.github,
            occupation=occupation,
            occupation_other=self.faker.job() if occupation == "" else "",
            affiliation=person.affiliation,
            location=self.faker.city(),
            country=choice(Countries)[0],
            underresourced=randbool(0.6),
            domains_other="",
            underrepresented=choice(underrepresented_choices)[0],
            underrepresented_details=choice(["", self.faker.paragraph(nb_sentences=1)]),
            nonprofit_teaching_experience="",
            previous_training=choice(TrainingRequest.PREVIOUS_TRAINING_CHOICES)[0],
            previous_training_other="",
            previous_training_explanation=self.faker.text(),
            previous_experience=choice(TrainingRequest.PREVIOUS_EXPERIENCE_CHOICES)[0],
            previous_experience_other="",
            programming_language_usage_frequency=choice(TrainingRequest.PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES)[
                0
            ],
            checkout_intent=choice(TrainingRequest.CHECKOUT_INTENT_CHOICES)[0],
            teaching_intent=choice(TrainingRequest.TEACHING_INTENT_CHOICES)[0],
            teaching_frequency_expectation=choice(TrainingRequest.TEACHING_FREQUENCY_EXPECTATION_CHOICES)[0],
            teaching_frequency_expectation_other="",
            max_travelling_frequency=choice(TrainingRequest.MAX_TRAVELLING_FREQUENCY_CHOICES)[0],
            max_travelling_frequency_other="",
            reason=self.faker.text(),
        )
        req.domains.set(sample(list(KnowledgeDomain.objects.all())))
        req.previous_involvement.set(sample(list(Role.objects.all())))

        if person_or_None is None:
            person.delete()

    def fake_person(self, *, is_instructor: bool, is_trainer: bool = False) -> Person:
        airport = choice(Airport.objects.all())

        email = choice(
            [
                self.faker.email(),
                self.faker.safe_email(),
                self.faker.free_email(),
                self.faker.company_email(),
            ]
        )

        gender = choice(Person.GENDER_CHOICES)[0]

        if gender == "F":
            personal_name = self.faker.first_name_female()
            family_name = self.faker.last_name_female()
        elif gender == "M":
            personal_name = self.faker.first_name_male()
            family_name = self.faker.last_name_male()
        else:
            personal_name = self.faker.first_name()
            family_name = self.faker.last_name()

        gender_other = ""
        if gender == "O":
            gender_other = self.faker.word().title()

        social_username = self.faker.user_name()

        if randbool(0.6):
            # automatically generate username
            username = create_username(personal_name, family_name)
        else:
            # assume that the username is provided by the person
            username = social_username

        github = social_username
        twitter = social_username
        bluesky = f"@{social_username}.bsky.social"
        mastodon = self.faker.url() if randbool(0.5) else None
        url = self.faker.url() if randbool(0.5) else ""

        person = Person.objects.create(
            personal=personal_name,
            family=family_name,
            email=email,
            gender=gender,
            gender_other=gender_other,
            airport=airport,
            twitter=twitter,
            bluesky=bluesky,
            mastodon=mastodon,
            github=github,
            url=url,
            username=username,
            country=choice(Countries)[0],
        )

        if is_instructor:
            # Add one or more instructor badges
            awards = []
            badges = sample(list(Badge.objects.instructor_badges()))
            for badge in badges:
                date = self.faker.date_time_between(start_date="-5y").date()
                awards.append(Award(person=person, badge=badge, awarded=date))
            Award.objects.bulk_create(awards)

            if randbool(0.75):
                # Add one or more qualifications
                Qualification.objects.bulk_create(
                    Qualification(person=person, lesson=lesson) for lesson in sample(list(Lesson.objects.all()))
                )

        if is_trainer:
            date = self.faker.date_time_between(start_date="-5y").date()
            trainer = Badge.objects.get(name="trainer")
            Award.objects.create(person=person, badge=trainer, awarded=date)

        return person

    def fake_organizations(self, count: int = 10) -> None:
        """Add some organizations that host events."""
        self.stdout.write("Generating {} fake organizations...".format(count))

        for _ in range(count):
            Organization.objects.create(
                domain=self.faker.domain_name(),
                fullname=self.faker.company(),
                country=choice(Countries)[0],
            )

    def real_organizations(self) -> None:
        """Add real Carpentries organizations."""
        self.stdout.write("Adding real organizations.")
        orgs = [
            ("self-organized", "self-organized"),
            ("Software Carpentry", "software-carpentry.org"),
            ("Data Carpentry", "datacarpentry.org"),
            ("Library Carpentry", "librarycarpentry.org"),
            ("Instructor Training", "carpentries.org"),
        ]
        for name, domain in orgs:
            _, created = Organization.objects.get_or_create(
                domain=domain,
                defaults=dict(fullname=name),
            )
            if created:
                self.stdout.write('Added "{}" organization.'.format(domain))

    def fake_membership_person_roles(self) -> None:
        self.stdout.write("Generating fake membership person roles...")
        MembershipPersonRole.objects.create(name="billing_contact", verbose_name="Billing Contact")
        MembershipPersonRole.objects.create(name="programmatic_contact", verbose_name="Programmatic Contact")

    def fake_memberships(self, count: int = 10) -> None:
        self.stdout.write("Generating {} fake memberships...".format(count))

        for _ in range(count):
            start = self.faker.date_time_between(start_date="-5y").date()
            organization_count = randint(1, 4)
            organization_generator = iter(Organization.objects.all().order_by("?"))
            name = self.faker.company()
            registration_code = name[:5] + str(randint(10, 99))
            membership = Membership.objects.create(
                name=name,
                consortium=organization_count > 1,
                variant=choice(Membership.MEMBERSHIP_CHOICES)[0],
                agreement_start=start,
                agreement_end=start + timedelta(days=365),
                contribution_type=choice(Membership.CONTRIBUTION_CHOICES)[0],
                registration_code=registration_code,
                workshops_without_admin_fee_per_agreement=randint(5, 15),
                public_instructor_training_seats=randint(5, 15),
                inhouse_instructor_training_seats=randint(5, 15),
            )
            members = [
                Member(
                    membership=membership,
                    organization=next(organization_generator),
                    role=choice(MemberRole.objects.all()),
                )
                for _ in range(organization_count)
            ]
            Member.objects.bulk_create(members)

    def fake_current_events(self, count: int = 5, **kwargs: Any) -> None:
        """Ongoing and upcoming events."""
        self.stdout.write("Generating {} fake current events...".format(count))

        for _ in range(count):
            self.fake_event(future_date=True, **kwargs)

    def fake_unpublished_events(self, count: int = 5) -> None:
        """Events with missing location data (which is required for publishing
        them)."""
        self.stdout.write("Generating {} fake unpublished events...".format(count))

        for _ in range(count):
            self.fake_event(location_data=False)

    def fake_self_organized_events(self, count: int = 5) -> None:
        """Full-blown events with 'self-organized' host."""
        self.stdout.write("Generating {} fake self organized events...".format(count))

        for _ in range(count):
            e = self.fake_event(self_organized=True)
            e.save()

    def fake_ttt_events(self, count: int = 10) -> None:
        self.stdout.write("Generating {} fake train-the-trainer events...".format(count))
        ttt_tag = Tag.objects.get(name="TTT")
        carpentries_org = Organization.objects.get(domain="carpentries.org")
        for _ in range(count):
            e = self.fake_event()
            e.slug += "-ttt"
            e.administrator = carpentries_org
            e.tags.set([ttt_tag])
            e.save()

    def fake_event(
        self,
        *,
        location_data: bool = True,
        self_organized: bool = False,
        add_tags: bool = True,
        future_date: bool = False,
    ) -> Event:
        if future_date:
            start = self.faker.date_time_between(start_date="now", end_date="+120d").date()
        else:
            start = self.faker.date_time_between(start_date="-120d").date()
        city = self.faker.city().replace(" ", "-").lower()
        if self_organized:
            org = Organization.objects.get(domain="self-organized")
            administrator = org
        else:
            org = choice(Organization.objects.exclude(domain="self-organized"))
            administrator = None

        # The following line may result in IntegrityError from time to time,
        # because we don't guarantee that the url is unique. In that case,
        # simply clear database and rerun fake_database command
        # (python manage.py fake_database). Be aware that recreating a database
        # deletes all data in the existing database!
        e = Event.objects.create(
            slug="{:%Y-%m-%d}-{}".format(start, city),
            start=start,
            end=start + timedelta(days=2),
            url=self.faker.unique_url(),
            host=org,
            administrator=administrator,
            # needed in order for event to be published
            country=choice(Countries)[0] if location_data else None,
            venue=self.faker.word().title() if location_data else "",
            address=self.faker.street_address() if location_data else "",
            latitude=uniform(-90, 90) if location_data else None,
            longitude=uniform(0, 180) if location_data else None,
            metadata_changed=randbool(0.1),
        )
        if add_tags:
            e.tags.set(sample(list(Tag.objects.exclude(name="TTT")), 2))
        return e

    def fake_tasks(self, count: int = 120) -> None:
        self.stdout.write("Generating {} fake tasks...".format(count))

        events = Event.objects.all()
        persons = Person.objects.all()
        roles = Role.objects.all()
        all_possible = list(itertools.product(events, persons, roles))

        for event, person, role in sample(all_possible, count):
            Task.objects.create(
                event=event,
                person=person,
                role=role,
            )

    def fake_unmatched_training_requests(self, count: int = 20) -> None:
        self.stdout.write("Generating {} fake unmatched training requests...".format(count))

        for _ in range(count):
            self.fake_training_request(None)

    def fake_duplicated_people(self, count: int = 5) -> None:
        self.stdout.write("Generating {} fake people duplications...".format(count))

        for _ in range(count):
            person = Person.objects.order_by("?")[0]
            person.id = None

            # avoid integrity errors due to unique constraints
            person.username = create_username(person.personal, person.family)
            person.twitter = None
            person.bluesky = None
            person.mastodon = None
            person.github = None
            person.email = self.faker.email()

            person.save()

    def get_or_invent_member_code(self) -> str:
        if randbool(0.5):
            # 50% of time, use an existing member code
            # may or may not be a valid choice depending on membership dates
            membership = choice(Membership.objects.all())
            member_code = membership.registration_code or ""
        elif randbool(0.5):
            # 25% of time, make up an invalid code
            member_code = self.faker.word()
        else:
            # 25% of time, don't use any code
            member_code = ""

        return member_code

    def fake_workshop_requests(self, count: int = 10) -> None:
        self.stdout.write("Generating {} fake workshop requests...".format(count))

        curricula = Curriculum.objects.filter(active=True)
        organizations = Organization.objects.all()

        for _ in range(count):
            if randbool(0.5):
                language = Language.objects.get(subtag="en")
            else:
                language = choice(Language.objects.all())

            if randbool(0.3):
                org = choice(organizations)
                org_name = ""
                org_url = ""
            else:
                org = None
                org_name = self.faker.company()
                org_url = self.faker.url()

            public_event = choice(WorkshopRequest.PUBLIC_EVENT_CHOICES)[0]
            public_event_other = self.faker.sentence() if public_event == "other" else ""

            online_inperson = choice(WorkshopRequest.ONLINE_INPERSON_CHOICES)[0]

            administrative_fee = choice(WorkshopRequest.FEE_CHOICES)[0]
            scholarship_circumstances = self.faker.sentence() if administrative_fee == "waiver" else ""
            travel_expences_management = choice(WorkshopRequest.TRAVEL_EXPENCES_MANAGEMENT_CHOICES)[0]
            travel_expences_management_other = self.faker.sentence() if travel_expences_management == "" else ""
            institution_restrictions = choice(WorkshopRequest.RESTRICTION_CHOICES)[0]
            institution_restrictions_other = self.faker.sentence() if institution_restrictions == "" else ""

            member_code = self.get_or_invent_member_code()
            req = WorkshopRequest.objects.create(
                state=choice(["p", "d", "a"]),
                data_privacy_agreement=randbool(0.5),
                code_of_conduct_agreement=randbool(0.5),
                host_responsibilities=randbool(0.5),
                personal=self.faker.first_name(),
                family=self.faker.last_name(),
                email=self.faker.email(),
                institution=org,
                institution_other_name=org_name,
                institution_other_URL=org_url,
                institution_department="",
                member_code=member_code,
                online_inperson=online_inperson,
                public_event=public_event,
                public_event_other=public_event_other,
                additional_contact=(
                    "Test Person <email@email.com>; Another Person <person@example.com>"  # use ";" as separator
                ),
                location=self.faker.city(),
                country=choice(Countries)[0],
                preferred_dates=self.faker.date_time_between(start_date="now", end_date="+1y").date(),
                other_preferred_dates="Alternatively: soon",
                language=language,
                audience_description=self.faker.sentence(),
                administrative_fee=administrative_fee,
                scholarship_circumstances=scholarship_circumstances,
                travel_expences_agreement=True,
                travel_expences_management=travel_expences_management,
                travel_expences_management_other=travel_expences_management_other,
                institution_restrictions=institution_restrictions,
                institution_restrictions_other=institution_restrictions_other,
                carpentries_info_source_other="",
                user_notes=self.faker.sentence(),
            )

            req.requested_workshop_types.set(sample(list(curricula)))
            req.carpentries_info_source.set(sample(list(InfoSource.objects.all())))
            req.save()

    def fake_workshop_inquiries(self, count: int = 10) -> None:
        self.stdout.write("Generating {} fake workshop inquiries...".format(count))

        curricula = Curriculum.objects.filter(active=True)
        organizations = Organization.objects.all()

        for _ in range(count):
            if randbool(0.5):
                language = Language.objects.get(subtag="en")
            else:
                language = choice(Language.objects.all())

            if randbool(0.3):
                org = choice(organizations)
                org_name = ""
                org_url = ""
            else:
                org = None
                org_name = self.faker.company()
                org_url = self.faker.url()

            public_event = choice(WorkshopInquiryRequest.PUBLIC_EVENT_CHOICES)[0]
            public_event_other = self.faker.sentence() if public_event == "other" else ""

            online_inperson = choice(WorkshopInquiryRequest.ONLINE_INPERSON_CHOICES)[0]

            administrative_fee = choice(WorkshopInquiryRequest.FEE_CHOICES)[0]
            travel_expences_management = choice(WorkshopInquiryRequest.TRAVEL_EXPENCES_MANAGEMENT_CHOICES)[0]
            travel_expences_management_other = self.faker.sentence() if travel_expences_management == "" else ""
            institution_restrictions = choice(WorkshopInquiryRequest.RESTRICTION_CHOICES)[0]
            institution_restrictions_other = self.faker.sentence() if institution_restrictions == "" else ""

            req = WorkshopInquiryRequest.objects.create(
                state=choice(["p", "d", "a"]),
                data_privacy_agreement=randbool(0.5),
                code_of_conduct_agreement=randbool(0.5),
                host_responsibilities=randbool(0.5),
                personal=self.faker.first_name(),
                family=self.faker.last_name(),
                email=self.faker.email(),
                institution=org,
                institution_other_name=org_name,
                institution_other_URL=org_url,
                institution_department="",
                online_inperson=online_inperson,
                public_event=public_event,
                public_event_other=public_event_other,
                additional_contact=(
                    "Test Person <email@email.com>; Another Person <person@example.com>"  # use ";" as separator
                ),
                location=self.faker.city(),
                country=choice(Countries)[0],
                routine_data_other="",
                domains_other="",
                audience_description=self.faker.sentence(),
                preferred_dates=self.faker.date_time_between(start_date="now", end_date="+1y").date(),
                other_preferred_dates="Alternatively: soon",
                language=language,
                administrative_fee=administrative_fee,
                travel_expences_agreement=True,
                travel_expences_management=travel_expences_management,
                travel_expences_management_other=travel_expences_management_other,
                institution_restrictions=institution_restrictions,
                institution_restrictions_other=institution_restrictions_other,
                carpentries_info_source_other="",
                user_notes=self.faker.sentence(),
            )

            req.routine_data.set(sample(list(DataVariant.objects.all())))
            req.domains.set(sample(list(KnowledgeDomain.objects.all())))
            req.academic_levels.set(sample(list(AcademicLevel.objects.all())))
            req.computing_levels.set(sample(list(ComputingExperienceLevel.objects.all())))
            req.requested_workshop_types.set(sample(list(curricula)))
            req.carpentries_info_source.set(sample(list(InfoSource.objects.all())))
            req.save()

    def fake_selforganised_submissions(self, count: int = 10) -> None:
        self.stdout.write("Generating {} fake self-organised submissions...".format(count))

        curricula = Curriculum.objects.filter(active=True)
        organizations = Organization.objects.all()

        for _ in range(count):
            if randbool(0.5):
                language = Language.objects.get(subtag="en")
            else:
                language = choice(Language.objects.all())

            if randbool(0.3):
                org = choice(organizations)
                org_name = ""
                org_url = ""
            else:
                org = None
                org_name = self.faker.company()
                org_url = self.faker.url()

            public_event = choice(SelfOrganisedSubmission.PUBLIC_EVENT_CHOICES)[0]
            public_event_other = self.faker.sentence() if public_event == "other" else ""

            online_inperson = choice(SelfOrganisedSubmission.ONLINE_INPERSON_CHOICES)[0]

            workshop_format = choice(SelfOrganisedSubmission.FORMAT_CHOICES)[0]
            workshop_format_other = self.faker.sentence() if workshop_format == "" else ""
            if randbool(0.5):
                workshop_types = list(curricula.filter(mix_match=True))
                workshop_types_explain = "\n".join([str(lesson) for lesson in Lesson.objects.order_by("?")[:10]])
            else:
                workshop_types = sample(list(curricula))
                workshop_types_explain = ""

            req = SelfOrganisedSubmission.objects.create(
                state=choice(["p", "d", "a"]),
                data_privacy_agreement=randbool(0.5),
                code_of_conduct_agreement=randbool(0.5),
                host_responsibilities=randbool(0.5),
                personal=self.faker.first_name(),
                family=self.faker.last_name(),
                email=self.faker.email(),
                institution=org,
                institution_other_name=org_name,
                institution_other_URL=org_url,
                institution_department="",
                online_inperson=online_inperson,
                public_event=public_event,
                public_event_other=public_event_other,
                additional_contact=(
                    "Test Person <email@email.com>; Another Person <person@example.com>"  # use ";" as separator
                ),
                workshop_url=self.faker.url(),
                workshop_format=workshop_format,
                workshop_format_other=workshop_format_other,
                workshop_types_other="",
                workshop_types_other_explain=workshop_types_explain,
                language=language,
            )

            req.workshop_types.set(workshop_types)
            req.save()

    def fake_consents(self) -> None:
        terms = Term.objects.active().prefetch_active_options()
        count = Person.objects.all().count() * len(terms)  # all persons * number of consents generated
        self.stdout.write("Generating {} fake consents...".format(count))

        consents: List[Consent] = []
        people = Person.objects.all()
        for person in people:
            for term in terms:
                consent = Consent(person=person, term_option=choice(list(term.options)), term=term)
                consents.append(consent)

        # Archive unset old consents before adding new ones
        Consent.objects.filter(
            person__in=people,
            term__in=terms,
        ).active().update(archived_at=timezone.now())
        Consent.objects.bulk_create(consents)

    def fake_instructor_recruitments(self) -> list[InstructorRecruitment]:
        """Create recruitments for new fake events.

        Two new recruitments will be created, one should be open, the other should be
        closed."""
        self.stdout.write("Generating 2 fake instructor recruitments...")

        assignee = Person.objects.get(username="admin")
        event1 = self.fake_event()
        recruitment1 = InstructorRecruitment.objects.create(
            assigned_to=assignee,
            status="o",
            notes=self.faker.paragraph(nb_sentences=1),
            event=event1,
        )
        event2 = self.fake_event()
        recruitment2 = InstructorRecruitment.objects.create(
            assigned_to=assignee,
            status="c",
            notes=self.faker.paragraph(nb_sentences=1),
            event=event2,
        )
        return [recruitment1, recruitment2]

    def fake_instructor_recruitment_signups(self, recruitments: list[InstructorRecruitment]) -> None:
        self.stdout.write(f"Generating {3 * len(recruitments)} fake instructor recruitment signups...")

        person1 = self.fake_person(is_instructor=True)
        person2 = self.fake_person(is_instructor=True)
        person3 = self.fake_person(is_instructor=True)

        for recruitment in recruitments:
            InstructorRecruitmentSignup.objects.create(
                state="p",
                recruitment=recruitment,
                person=person1,
                interest="session",
                user_notes=self.faker.paragraph(nb_sentences=2),
                notes=self.faker.paragraph(nb_sentences=1),
            )
            InstructorRecruitmentSignup.objects.create(
                state="d",
                recruitment=recruitment,
                person=person2,
                interest="session",
                user_notes=self.faker.paragraph(nb_sentences=2),
                notes=self.faker.paragraph(nb_sentences=1),
            )
            InstructorRecruitmentSignup.objects.create(
                state="a",
                recruitment=recruitment,
                person=person3,
                interest="session",
                user_notes=self.faker.paragraph(nb_sentences=2),
                notes=self.faker.paragraph(nb_sentences=1),
            )

    def fake_consortiums(self) -> None:
        self.stdout.write("Generating 5 fake consortiums...")

        for _ in range(5):
            Consortium.objects.create(name=self.faker.company(), description=self.faker.paragraph())

    def fake_partnerships(self) -> None:
        self.stdout.write("Generating 4 fake partnerships...")

        partner_consortium = Consortium.objects.all()[0]
        start = self.faker.date_time_between(start_date="-1y").date()
        Partnership.objects.create(
            name=partner_consortium.name,
            tier="First tier",  # TODO: may become FK in future
            agreement_start=start,
            agreement_end=start + timedelta(days=365),
            extensions=[],
            rolled_to_partnership=None,
            agreement_link=self.faker.url(),
            registration_code=self.faker.slug(),
            public_status=choice(Partnership.PUBLIC_STATUS_CHOICES)[0],
            partner_consortium=partner_consortium,
            partner_organization=None,
        )

        partner_organization = Organization.objects.all()[0]
        start = self.faker.date_time_between(start_date="-1y").date()
        Partnership.objects.create(
            name=partner_organization.fullname,
            tier="First tier",  # TODO: may become FK in future
            agreement_start=start,
            agreement_end=start + timedelta(days=365),
            extensions=[],
            rolled_to_partnership=None,
            agreement_link=self.faker.url(),
            registration_code=self.faker.slug(),
            public_status=choice(Partnership.PUBLIC_STATUS_CHOICES)[1],
            partner_consortium=None,
            partner_organization=partner_organization,
        )

        partner_organization = Organization.objects.all()[1]
        start1 = self.faker.date_time_between(start_date="-2y").date()
        start2 = start1 + timedelta(days=366)

        newer = Partnership.objects.create(
            name=partner_organization.fullname,
            tier="First tier",  # TODO: may become FK in future
            agreement_start=start2,
            agreement_end=start2 + timedelta(days=365),
            extensions=[],
            rolled_to_partnership=None,
            agreement_link=self.faker.url(),
            registration_code=self.faker.slug(),
            public_status=choice(Partnership.PUBLIC_STATUS_CHOICES)[1],
            partner_consortium=None,
            partner_organization=partner_organization,
        )

        Partnership.objects.create(
            name=partner_organization.fullname,
            tier="First tier",  # TODO: may become FK in future
            agreement_start=start1,
            agreement_end=start1 + timedelta(days=365),
            extensions=[],
            rolled_to_partnership=newer,
            agreement_link=self.faker.url(),
            registration_code=self.faker.slug(),
            public_status=choice(Partnership.PUBLIC_STATUS_CHOICES)[1],
            partner_consortium=None,
            partner_organization=partner_organization,
        )

    def handle(self, *args: Any, **options: Any) -> None:
        seed = options["seed"]
        if seed is not None:
            Faker.seed(seed)

        try:
            self.fake_groups()
            self.fake_airports()
            self.fake_roles()
            self.fake_tags()
            self.fake_instructors()
            self.fake_trainers()
            self.fake_admins()
            self.fake_organizations()
            self.real_organizations()
            self.fake_membership_person_roles()
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
            self.fake_selforganised_submissions()
            self.fake_consents()
            recruitments = self.fake_instructor_recruitments()
            self.fake_instructor_recruitment_signups(recruitments)

            self.fake_consortiums()
            self.fake_partnerships()

            # self.fake_accounts()
            # self.fake_account_owners()
            # self.fake_benefits()
            # self.fake_account_benefits()
        except IntegrityError as e:
            print("!!!" * 10)
            print("Delete the database, and rerun this script.")
            print("!!!" * 10)
            raise e
