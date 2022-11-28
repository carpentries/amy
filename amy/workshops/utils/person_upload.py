import csv
from io import TextIOBase
import logging
from typing import Literal

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
import django_rq

from autoemails.actions import NewInstructorAction, NewSupportingInstructorAction
from autoemails.base_views import ActionManageMixin
from autoemails.models import Trigger
from workshops.exceptions import InternalError
from workshops.models import Event, Person, Role, Task
from workshops.utils.usernames import create_username

logger = logging.getLogger("amy")
scheduler = django_rq.get_scheduler("default")


def upload_person_task_csv(
    stream: TextIOBase,
) -> tuple[list, list[Literal["personal", "family", "email"]]]:
    """Read people from CSV and return a JSON-serializable list of dicts.

    The input `stream` should be a file-like object that returns
    Unicode data.

    "Serializability" is required because we put this data into session.  See
    https://docs.djangoproject.com/en/1.7/topics/http/sessions/ for details.

    Also return a list of fields from Person.PERSON_UPLOAD_FIELDS for which
    no data was given.
    """

    result = []
    reader = csv.DictReader(stream)
    empty_fields = set()

    for row in reader:
        # skip empty lines in the CSV
        if not any(row.values()):
            continue

        entry = {}
        for col in Person.PERSON_UPLOAD_FIELDS:
            try:
                entry[col] = row[col].strip()
            except (KeyError, IndexError, AttributeError):
                # either `col` is not in `entry`, or not in `row`, or
                # `.strip()` doesn't work (e.g. `row[col]` gives `None` instead
                # of string)
                entry[col] = None
                empty_fields.add(col)

        for col in Person.PERSON_TASK_EXTRA_FIELDS:
            entry[col] = row.get(col, None)
        entry["errors"] = None

        # it will be set in the `verify_upload_person_task`
        entry["username"] = ""

        result.append(entry)

    return result, list(empty_fields)


def verify_upload_person_task(data, match=False):
    """
    Verify that uploaded data is correct.  Show errors by populating `errors`
    dictionary item.  This function changes `data` in place.

    If `match` provided, it will try to match with first similar person.
    """

    errors_occur = False
    for item in data:
        errors = []
        info = []

        event = item.get("event", None)
        existing_event = None
        if event:
            try:
                existing_event = Event.objects.get(slug=event)
            except Event.DoesNotExist:
                errors.append('Event with slug "{0}" does not exist.'.format(event))
            except Event.MultipleObjectsReturned:
                errors.append('More than one event named "{0}" exists.'.format(event))

        role = item.get("role", None)
        existing_role = None
        if role:
            try:
                existing_role = Role.objects.get(name=role)
            except Role.DoesNotExist:
                errors.append('Role with name "{0}" does not exist.'.format(role))
            except Role.MultipleObjectsReturned:
                errors.append('More than one role named "{0}" exists.'.format(role))

        # check if the user exists, and if so: check if existing user's
        # personal and family names are the same as uploaded
        email = item.get("email", "")
        personal = item.get("personal", "")
        family = item.get("family", "")
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
                info.append(
                    "Could not match selected person. New record will " "be created."
                )
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
                if item.get("username"):
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
            item["username"] = person.username
            item["existing_person_id"] = person_id
            item["person_exists"] = True
        else:
            # force a newly created username
            if not item.get("username"):
                item["username"] = create_username(personal, family)
            item["person_exists"] = False

            info.append("Person and task will be created.")

        # let's check if there's someone else named this way
        similar_persons = Person.objects.filter(
            Q(personal=personal, family=family)
            | Q(email=email) & ~Q(email="") & Q(email__isnull=False)
        )
        # need to cast to list, otherwise it won't JSON-ify
        item["similar_persons"] = list(
            zip(
                similar_persons.values_list("id", flat=True),
                map(lambda x: str(x), similar_persons),
            )
        )

        if existing_event and person and existing_role:
            # person, their role and a corresponding event exist, so
            # let's check if the task exists
            try:
                Task.objects.get(
                    event=existing_event, person=person, role=existing_role
                )
            except Task.DoesNotExist:
                info.append("Task will be created.")
            else:
                info.append("Task already exists.")

        # let's check what Person model validators want to say
        try:
            p = Person(
                personal=personal, family=family, email=email, username=item["username"]
            )
            p.clean_fields(exclude=["password"])
        except ValidationError as e:
            if e.message_dict:  # to get rid of type error in line below
                for k, v in e.message_dict.items():
                    errors.append("{}: {}".format(k, v))

        if not role:
            errors.append("Must have a role.")

        if not event:
            errors.append("Must have an event.")

        item["errors"] = errors
        if errors:
            errors_occur = True

        item["info"] = info

    return errors_occur


def create_uploaded_persons_tasks(data, request=None):
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
            row_repr = (
                "{personal} {family} {username} <{email}>, {role} at {event}"
            ).format(**row)

            try:
                fields = {key: row[key] for key in Person.PERSON_UPLOAD_FIELDS}
                fields["username"] = row["username"]

                if row["person_exists"] and row["existing_person_id"]:
                    # we should use existing Person
                    p = Person.objects.get(pk=row["existing_person_id"])

                elif row["person_exists"] and not row["existing_person_id"]:
                    # we should use existing Person
                    p = Person.objects.get(
                        personal=fields["personal"],
                        family=fields["family"],
                        username=fields["username"],
                        email=fields["email"],
                    )

                else:
                    # we should create a new Person without any email provided
                    p = Person(**fields)
                    p.save()
                    persons_created.append(p)

                if row["event"] and row["role"]:
                    e = Event.objects.get(slug=row["event"])
                    r = Role.objects.get(name=row["role"])

                    # if the number of learners attending the event changed,
                    # we should update ``event.attendance``
                    if row["role"] == "learner":
                        events.add(e)

                    t, created = Task.objects.get_or_create(person=p, event=e, role=r)
                    if created:
                        tasks_created.append(t)

            except IntegrityError as e:
                raise IntegrityError('{0} (for "{1}")'.format(str(e), row_repr))

            except ObjectDoesNotExist as e:
                raise ObjectDoesNotExist('{0} (for "{1}")'.format(str(e), row_repr))

    jobs_created = []
    rqjobs_created = []

    # for each created task, try to add a new-(supporting)-instructor action
    with transaction.atomic():
        for task in tasks_created:
            # conditions check out
            if NewInstructorAction.check(task):
                objs = dict(task=task, event=task.event)
                # prepare context and everything and create corresponding RQJob
                jobs, rqjobs = ActionManageMixin.add(
                    action_class=NewInstructorAction,
                    logger=logger,
                    scheduler=scheduler,
                    triggers=Trigger.objects.filter(
                        active=True, action="new-instructor"
                    ),
                    context_objects=objs,
                    object_=task,
                    request=request,
                )
                jobs_created += jobs
                rqjobs_created += rqjobs

            # conditions check out
            if NewSupportingInstructorAction.check(task):
                objs = dict(task=task, event=task.event)
                # prepare context and everything and create corresponding RQJob
                jobs, rqjobs = ActionManageMixin.add(
                    action_class=NewSupportingInstructorAction,
                    logger=logger,
                    scheduler=scheduler,
                    triggers=Trigger.objects.filter(
                        active=True, action="new-supporting-instructor"
                    ),
                    context_objects=objs,
                    object_=task,
                    request=request,
                )
                jobs_created += jobs
                rqjobs_created += rqjobs

    return persons_created, tasks_created
