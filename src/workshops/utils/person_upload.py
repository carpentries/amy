import contextlib
import csv
import logging
from io import TextIOBase
from typing import Literal, NotRequired, TypedDict

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpRequest

from src.workshops.consts import IATA_AIRPORTS
from src.workshops.exceptions import InternalError
from src.workshops.models import Event, Person, Role, Task
from src.workshops.utils.usernames import create_username

logger = logging.getLogger("amy")


class PersonTaskEntry(TypedDict):
    personal: str
    family: str
    username: str
    email: str | None
    airport_iata: str
    event: str | None
    role: str | None
    errors: list[str]
    info: list[str]
    existing_person_id: NotRequired[int | None]
    person_exists: NotRequired[bool]
    similar_persons: NotRequired[list[tuple[int, str]]]


def upload_person_task_csv(
    stream: TextIOBase,
) -> tuple[list[PersonTaskEntry], set[Literal["personal", "family", "email"]]]:
    """Read people from CSV and return a JSON-serializable list of dicts.

    The input `stream` should be a file-like object that returns
    Unicode data.

    "Serializability" is required because we put this data into session.  See
    https://docs.djangoproject.com/en/1.7/topics/http/sessions/ for details.

    Also return a set of fields {"personal", "family", "email"} for which
    no data was given.
    """
    result = []
    reader = csv.DictReader(stream)
    empty_fields: set[Literal["personal", "family", "email"]] = set()

    for row in reader:
        # skip empty lines in the CSV
        if not any(row.values()):
            continue

        entry: PersonTaskEntry = {
            "personal": "",
            "family": "",
            "email": None,
            "airport_iata": "",
            "event": None,
            "role": None,
            "errors": [],
            "info": [],
            "username": "",  # it will be set in the `verify_upload_person_task`
        }

        for base_column in Person.PERSON_UPLOAD_FIELDS:
            try:
                entry[base_column] = row[base_column].strip()
            except (KeyError, IndexError, AttributeError):
                # either `base_column` is not in `entry`, or not in `row`, or
                # `.strip()` doesn't work (e.g. `row[base_column]` gives `None` instead
                # of string)
                empty_fields.add(base_column)

        for additional_column in Person.PERSON_TASK_EXTRA_FIELDS:
            with contextlib.suppress(KeyError):
                entry[additional_column] = row[additional_column]

        result.append(entry)

    return (
        result,
        empty_fields,
    )


def verify_upload_person_task(data: list[PersonTaskEntry], match: bool = False) -> bool:
    """
    Verify that uploaded data is correct.  Show errors by populating `errors`
    dictionary item.  This function changes `data` in place.

    If `match` provided, it will try to match with first similar person.
    """

    errors_occur = False
    for item in data:
        errors = []
        info = []

        event = item["event"]
        existing_event = None
        if event:
            try:
                existing_event = Event.objects.get(slug=event)
            except Event.DoesNotExist:
                errors.append(f'Event with slug "{event}" does not exist.')
            except Event.MultipleObjectsReturned:
                errors.append(f'More than one event named "{event}" exists.')

        role = item["role"]
        existing_role = None
        if role:
            try:
                existing_role = Role.objects.get(name=role)
            except Role.DoesNotExist:
                errors.append(f'Role with name "{role}" does not exist.')
            except Role.MultipleObjectsReturned:
                errors.append(f'More than one role named "{role}" exists.')

        airport_iata = item["airport_iata"]
        if airport_iata:
            try:
                IATA_AIRPORTS[airport_iata]
            except KeyError:
                errors.append(f'Airport with IATA code "{airport_iata}" does not exist.')

        # check if the user exists, and if so: check if existing user's
        # personal and family names are the same as uploaded
        email = item["email"]
        personal = item["personal"]
        family = item["family"]
        person_id = item.get("existing_person_id", None)
        person = None

        # try to match with first similar person
        if match is True:
            try:
                person = Person.objects.get(email=email)
            except (Person.DoesNotExist, Person.MultipleObjectsReturned):
                person = None
            else:
                info.append("Existing record for person will be used.")
                person_id = person.pk

        elif person_id:
            try:
                person = Person.objects.get(id=int(person_id))
            except (ValueError, TypeError, Person.DoesNotExist):
                person = None
                info.append("Could not match selected person. New record will be created.")
            else:
                info.append("Existing record for person will be used.")

        elif not person_id:
            try:
                Person.objects.get(email=email)
            except (Person.DoesNotExist, Person.MultipleObjectsReturned):
                pass
            else:
                errors.append("Person with this email address already exists.")

            try:
                if item["username"]:
                    Person.objects.get(username=item.get("username"))
            except Person.DoesNotExist:
                pass
            else:
                errors.append("Person with this username already exists.")

        if not email and not person:
            info.append("It's highly recommended to add an email address.")

        if person:
            # force details from existing record
            item["personal"] = personal = person.personal
            item["family"] = family = person.family
            item["email"] = email = person.email
            item["airport_iata"] = airport_iata = person.airport_iata
            item["username"] = person.username
            item["existing_person_id"] = person_id
            item["person_exists"] = True
        else:
            # force a newly created username
            if not item["username"]:
                item["username"] = create_username(personal, family)
            item["person_exists"] = False

            info.append("Person and task will be created.")

        # check if there's someone else named this way
        similar_persons = Person.objects.filter(
            Q(personal=personal, family=family) | Q(email=email) & ~Q(email="") & Q(email__isnull=False)
        )
        # need to cast to list, otherwise it won't JSON-ify
        item["similar_persons"] = list(
            zip(
                similar_persons.values_list("id", flat=True),
                map(lambda x: str(x), similar_persons),
                strict=True,
            )
        )

        if existing_event and person and existing_role:
            # person, their role and a corresponding event exist, so
            # let's check if the task exists
            try:
                Task.objects.get(event=existing_event, person=person, role=existing_role)
            except Task.DoesNotExist:
                info.append("Task will be created.")
            else:
                info.append("Task already exists.")

        # let's check what Person model validators want to say
        try:
            p = Person(
                personal=personal, family=family, email=email, username=item["username"], airport_iata=airport_iata
            )
            p.clean_fields(exclude=["password"])
        except ValidationError as e:
            if e.message_dict:  # to get rid of type error in line below
                for k, v in e.message_dict.items():
                    errors.append(f"{k}: {v}")

        if not role:
            errors.append("Must have a role.")

        if not event:
            errors.append("Must have an event.")

        item["errors"] = errors
        if errors:
            errors_occur = True

        item["info"] = info

    return errors_occur


def create_uploaded_persons_tasks(
    data: list[PersonTaskEntry], request: HttpRequest | None = None
) -> tuple[list[Person], list[Task]]:
    """
    Create persons and tasks from upload data.
    """

    # Quick sanity check.
    if any([row.get("errors") for row in data]):
        raise InternalError("Uploaded data contains errors, cancelling upload")

    persons_created = []
    tasks_created = []
    events = set()

    with transaction.atomic():
        for row in data:
            row_repr = ("{personal} {family} {username} <{email}>, {role} at {event}").format(**row)

            try:
                fields = {
                    "personal": row["personal"],
                    "family": row["family"],
                    "email": row["email"],
                    "username": row["username"],
                    "airport_iata": row["airport_iata"],
                }

                if row["person_exists"] and row["existing_person_id"]:
                    # we should use existing Person
                    person = Person.objects.get(pk=row["existing_person_id"])

                elif row["person_exists"] and not row["existing_person_id"]:
                    # we should use existing Person
                    person = Person.objects.get(
                        personal=fields["personal"],
                        family=fields["family"],
                        username=fields["username"],
                        email=fields["email"],
                    )

                else:
                    # we should create a new Person without any email provided
                    person = Person(**fields)
                    person.save()
                    persons_created.append(person)

                if row["event"] and row["role"]:
                    event = Event.objects.get(slug=row["event"])
                    role = Role.objects.get(name=row["role"])

                    # if the number of learners attending the event changed,
                    # we should update ``event.attendance``
                    if row["role"] == "learner":
                        events.add(event)

                    task, created = Task.objects.get_or_create(person=person, event=event, role=role)
                    if created:
                        tasks_created.append(task)

            except IntegrityError as event:
                raise IntegrityError(f'{str(event)} (for "{row_repr}")') from event

            except ObjectDoesNotExist as event:
                raise ObjectDoesNotExist(f'{str(event)} (for "{row_repr}")') from event

    return persons_created, tasks_created
