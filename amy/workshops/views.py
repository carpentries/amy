import csv
import datetime
from functools import partial
import io
import logging
import re

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.models import Permission
from django.contrib.auth.views import logout_then_login
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
)
from django.db import IntegrityError
from django.db.models import (
    Case,
    When,
    Value,
    IntegerField,
    Count,
    Q,
    F,
    ProtectedError,
    Sum,
    Prefetch,
)
from django.forms import HiddenInput
from django.http import Http404, HttpResponse, JsonResponse
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django_comments.models import Comment
import django_rq
from github.GithubException import GithubException
from reversion.models import Version, Revision
from reversion_compare.forms import SelectDiffForm

from autoemails.actions import (
    NewInstructorAction,
    NewSupportingInstructorAction,
    PostWorkshopAction,
    InstructorsHostIntroductionAction,
    AskForWebsiteAction,
    RecruitHelpersAction,
)
from autoemails.models import Trigger
from autoemails.base_views import ActionManageMixin
from fiscal.forms import SponsorshipForm
from workshops.base_views import (
    AMYCreateView,
    AMYUpdateView,
    AMYDeleteView,
    AMYListView,
    RedirectSupportMixin,
    PrepopulationSupportMixin,
    AMYDetailView,
    AssignView,
)
from workshops.filters import (
    EventFilter,
    PersonFilter,
    TaskFilter,
    AirportFilter,
    BadgeAwardsFilter,
    WorkshopStaffFilter,
)
from workshops.forms import (
    SearchForm,
    WorkshopStaffForm,
    PersonForm,
    BulkUploadCSVForm,
    EventForm,
    EventCreateForm,
    TaskForm,
    AwardForm,
    PersonPermissionsForm,
    PersonsSelectionForm,
    BootstrapHelper,
    AdminLookupForm,
    EventsSelectionForm,
    EventsMergeForm,
    PersonsMergeForm,
    PersonCreateForm,
    ActionRequiredPrivacyForm,
)
from workshops.management.commands.check_for_workshop_websites_updates import (
    Command as WebsiteUpdatesCommand,
)
from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    Qualification,
    Person,
    Role,
    Organization,
    Membership,
    Sponsorship,
    Tag,
    Task,
    TrainingRequest,
)
from workshops.signals import create_comment_signal
from workshops.util import (
    upload_person_task_csv,
    verify_upload_person_task,
    create_uploaded_persons_tasks,
    InternalError,
    WrongWorkshopURL,
    fetch_workshop_metadata,
    parse_workshop_metadata,
    validate_workshop_metadata,
    assignment_selection,
    get_pagination_items,
    failed_to_delete,
    merge_objects,
    create_username,
    admin_required,
    OnlyForAdminsMixin,
    login_required,
    add_comment,
)


logger = logging.getLogger("amy.signals")
scheduler = django_rq.get_scheduler("default")
redis_connection = django_rq.get_connection("default")


@login_required
def logout_then_login_with_msg(request):
    messages.success(request, "You were successfully logged-out.")
    return logout_then_login(request)


@admin_required
def changes_log(request):
    log = (
        Revision.objects.all()
        .select_related("user")
        .prefetch_related("version_set")
        .order_by("-date_created")
    )
    log = get_pagination_items(request, log)
    context = {"log": log}
    return render(request, "workshops/changes_log.html", context)


# ------------------------------------------------------------

AIRPORT_FIELDS = ["iata", "fullname", "country", "latitude", "longitude"]


class AllAirports(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_airports"
    queryset = Airport.objects.all()
    filter_class = AirportFilter
    template_name = "workshops/all_airports.html"
    title = "All Airports"


class AirportDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = Airport.objects.all()
    context_object_name = "airport"
    template_name = "workshops/airport.html"
    slug_url_kwarg = "airport_iata"
    slug_field = "iata"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Airport {0}".format(self.object)
        return context


class AirportCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView):
    permission_required = "workshops.add_airport"
    model = Airport
    fields = AIRPORT_FIELDS


class AirportUpdate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = "workshops.change_airport"
    model = Airport
    fields = AIRPORT_FIELDS
    slug_field = "iata"
    slug_url_kwarg = "airport_iata"


class AirportDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Airport
    slug_field = "iata"
    slug_url_kwarg = "airport_iata"
    permission_required = "workshops.delete_airport"
    success_url = reverse_lazy("all_airports")


# ------------------------------------------------------------


class AllPersons(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_persons"
    template_name = "workshops/all_persons.html"
    filter_class = PersonFilter
    queryset = Person.objects.prefetch_related(
        Prefetch(
            "badges",
            to_attr="important_badges",
            queryset=Badge.objects.filter(name__in=Badge.IMPORTANT_BADGES),
        ),
    )
    title = "All Persons"


class PersonDetails(OnlyForAdminsMixin, AMYDetailView):
    context_object_name = "person"
    template_name = "workshops/person.html"
    pk_url_kwarg = "person_id"
    queryset = (
        Person.objects.annotate(
            num_taught=Count(
                Case(
                    When(task__role__name="instructor", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
            num_helper=Count(
                Case(
                    When(task__role__name="helper", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
            num_learner=Count(
                Case(
                    When(task__role__name="learner", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),

            num_supporting=Count(
                Case(
                    When(task__role__name="supporting-instructor", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
        )
        .prefetch_related(
            "award_set__badge",
            "award_set__awarded_by",
            "award_set__event",
            "task_set__role",
            "task_set__event",
            Prefetch(
                "task_set",
                to_attr="training_tasks",
                queryset=Task.objects.filter(
                    role__name="learner", event__tags__name="TTT"
                ),
            ),
        )
        .select_related("airport")
        .order_by("family", "personal")
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["title"] = "Person {0}".format(self.object)

        is_usersocialauth_in_sync = len(self.object.github_usersocialauth) > 0
        context["is_usersocialauth_in_sync"] = is_usersocialauth_in_sync

        return context


@admin_required
def person_bulk_add_template(request):
    """Dynamically generate a CSV template that can be used to bulk-upload people."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=BulkPersonAddTemplate.csv"

    writer = csv.writer(response)
    writer.writerow(Person.PERSON_TASK_UPLOAD_FIELDS)
    return response


@admin_required
@permission_required(
    ["workshops.add_person", "workshops.change_person"], raise_exception=True
)
def person_bulk_add(request):
    if request.method == "POST":
        form = BulkUploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            charset = request.FILES["file"].charset or settings.DEFAULT_CHARSET
            stream = io.TextIOWrapper(request.FILES["file"].file, charset)
            try:
                persons_tasks, empty_fields = upload_person_task_csv(stream)
            except csv.Error as e:
                messages.error(
                    request, "Error processing uploaded .CSV file: {}".format(e)
                )
            except UnicodeDecodeError:
                messages.error(
                    request, "Please provide a file in {} encoding.".format(charset)
                )
            else:
                if empty_fields:
                    msg_template = (
                        "The following required fields were not"
                        " found in the uploaded file: {}"
                    )
                    msg = msg_template.format(", ".join(empty_fields))
                    messages.error(request, msg)
                else:
                    # instead of insta-saving, put everything into session
                    # then redirect to confirmation page which in turn saves
                    # the data
                    request.session["bulk-add-people"] = persons_tasks
                    # request match
                    request.session["bulk-add-people-match"] = True
                    return redirect("person_bulk_add_confirmation")

    else:
        form = BulkUploadCSVForm()

    context = {
        "title": "Bulk Add People",
        "form": form,
        "charset": settings.DEFAULT_CHARSET,
        "roles": Role.objects.all(),
    }
    return render(request, "workshops/person_bulk_add_form.html", context)


@admin_required
@permission_required(
    ["workshops.add_person", "workshops.change_person"], raise_exception=True
)
def person_bulk_add_confirmation(request):
    """
    This view allows for manipulating and saving session-stored upload data.
    """
    persons_tasks = request.session.get("bulk-add-people")
    match = request.session.get("bulk-add-people-match", False)

    # if the session is empty, add message and redirect
    if not persons_tasks:
        messages.warning(request, "Could not locate CSV data, please " "upload again.")
        return redirect("person_bulk_add")

    if request.method == "POST":
        # update values if user wants to change them
        personals = request.POST.getlist("personal")
        families = request.POST.getlist("family")
        usernames = request.POST.getlist("username")
        emails = request.POST.getlist("email")
        events = request.POST.getlist("event")
        roles = request.POST.getlist("role")
        data_update = zip(personals, families, usernames, emails, events, roles)
        for k, record in enumerate(data_update):
            personal, family, username, email, event, role = record
            existing_person_id = persons_tasks[k].get("existing_person_id")
            # "field or None" converts empty strings to None values
            persons_tasks[k] = {
                "personal": personal,
                "family": family,
                "username": username,
                "email": email or None,
                "existing_person_id": existing_person_id,
            }
            # when user wants to drop related event they will send empty string
            # so we should unconditionally accept new value for event even if
            # it's an empty string
            persons_tasks[k]["event"] = event
            persons_tasks[k]["role"] = role
            persons_tasks[k]["errors"] = None  # reset here

        # save updated data to the session
        request.session["bulk-add-people"] = persons_tasks

        # check if user wants to verify or save, or cancel
        if request.POST.get("verify", None):
            # if there's "verify" in POST, then do only verification
            any_errors = verify_upload_person_task(persons_tasks)
            if any_errors:
                messages.error(
                    request, "Please make sure to fix all errors " "listed below."
                )

        # there must be "confirm" and no "cancel" in POST in order to save
        elif request.POST.get("confirm", None) and not request.POST.get("cancel", None):
            try:
                # verification now makes something more than database
                # constraints so we should call it first
                verify_upload_person_task(persons_tasks)
                persons_created, tasks_created = create_uploaded_persons_tasks(
                    persons_tasks, request=request
                )
            except (IntegrityError, ObjectDoesNotExist, InternalError) as e:
                messages.error(
                    request,
                    "Error saving data to the database: {}. "
                    "Please make sure to fix all errors "
                    "listed below.".format(e),
                )
                any_errors = verify_upload_person_task(persons_tasks)

            else:
                request.session["bulk-add-people"] = None
                messages.success(
                    request,
                    "Successfully created {0} persons and {1} tasks.".format(
                        len(persons_created), len(tasks_created)
                    ),
                )
                return redirect("person_bulk_add")

        else:
            # any "cancel" or no "confirm" in POST cancels the upload
            request.session["bulk-add-people"] = None
            return redirect("person_bulk_add")

    else:
        # alters persons_tasks via reference
        any_errors = verify_upload_person_task(persons_tasks, match=bool(match))
        request.session["bulk-add-people-match"] = False

    roles = Role.objects.all().values_list("name", flat=True)

    context = {
        "title": "Confirm uploaded data",
        "persons_tasks": persons_tasks,
        "any_errors": any_errors,
        "possible_roles": roles,
    }
    return render(request, "workshops/person_bulk_add_results.html", context)


@admin_required
@permission_required(
    ["workshops.add_person", "workshops.change_person"], raise_exception=True
)
def person_bulk_add_remove_entry(request, entry_id):
    "Remove specific entry from the session-saved list of people to be added."
    persons_tasks = request.session.get("bulk-add-people")

    if persons_tasks:
        entry_id = int(entry_id)
        try:
            del persons_tasks[entry_id]
            request.session["bulk-add-people"] = persons_tasks

        except IndexError:
            messages.warning(
                request, "Could not find specified entry #{}".format(entry_id)
            )

        return redirect(person_bulk_add_confirmation)

    else:
        messages.warning(
            request, "Could not locate CSV data, please try the " "upload again."
        )
        return redirect("person_bulk_add")


@admin_required
@permission_required(
    ["workshops.add_person", "workshops.change_person"], raise_exception=True
)
def person_bulk_add_match_person(request, entry_id, person_id=None):
    """Save information about matched person in the session-saved data."""
    persons_tasks = request.session.get("bulk-add-people")
    if not persons_tasks:
        messages.warning(
            request, "Could not locate CSV data, please try the " "upload again."
        )
        return redirect("person_bulk_add")

    if person_id is None:
        # unmatch
        try:
            entry_id = int(entry_id)

            persons_tasks[entry_id]["existing_person_id"] = 0
            request.session["bulk-add-people"] = persons_tasks

        except ValueError:
            # catches invalid argument for int()
            messages.warning(
                request,
                "Invalid entry ID ({}) or person ID "
                "({}).".format(entry_id, person_id),
            )

        except IndexError:
            # catches index out of bound
            messages.warning(
                request, "Could not find specified entry #{}".format(entry_id)
            )

        return redirect(person_bulk_add_confirmation)

    else:
        # match
        try:
            entry_id = int(entry_id)
            person_id = int(person_id)

            persons_tasks[entry_id]["existing_person_id"] = person_id
            request.session["bulk-add-people"] = persons_tasks

        except ValueError:
            # catches invalid argument for int()
            messages.warning(
                request,
                "Invalid entry ID ({}) or person ID "
                "({}).".format(entry_id, person_id),
            )

        except IndexError:
            # catches index out of bound
            messages.warning(
                request, "Could not find specified entry #{}".format(entry_id)
            )

        return redirect(person_bulk_add_confirmation)


class PersonCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView):
    permission_required = "workshops.add_person"
    model = Person
    form_class = PersonCreateForm

    def form_valid(self, form):
        """Person.lessons uses an intermediary model so we need to manually add
        objects of that model.

        See more here: http://stackoverflow.com/a/15745652"""
        self.object = form.save(commit=False)  # don't save M2M fields

        self.object.username = create_username(
            personal=form.cleaned_data["personal"], family=form.cleaned_data["family"]
        )

        # Need to save that object because of commit=False previously.
        # This doesn't save our troublesome M2M field.
        self.object.save()

        # send a signal to add a comment
        create_comment_signal.send(
            sender=self.form_class,
            content_object=self.object,
            comment=form.cleaned_data["comment"],
            timestamp=None,
        )

        # saving intermediary M2M model: Qualification
        for lesson in form.cleaned_data["lessons"]:
            Qualification.objects.create(lesson=lesson, person=self.object)

        # Important: we need to use ModelFormMixin.form_valid() here!
        # But by doing so we omit SuccessMessageMixin completely, so we need to
        # simulate it.  The code below is almost identical to
        # SuccessMessageMixin.form_valid().
        response = super().form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return response

    def get_initial(self):
        initial = {
            "personal": self.request.GET.get("personal", ""),
            "family": self.request.GET.get("family", ""),
            "email": self.request.GET.get("email", ""),
        }
        return initial


class PersonUpdate(OnlyForAdminsMixin, UserPassesTestMixin, AMYUpdateView):
    model = Person
    form_class = PersonForm
    pk_url_kwarg = "person_id"
    template_name = "workshops/person_edit_form.html"

    def test_func(self):
        if not (
            self.request.user.has_perm("workshops.change_person")
            or self.request.user == self.get_object()
        ):
            raise PermissionDenied
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kwargs = {
            "initial": {"person": self.object},
            "widgets": {"person": HiddenInput()},
        }
        context.update(
            {
                "awards": self.object.award_set.select_related(
                    "event", "badge"
                ).order_by("badge__name"),
                "tasks": self.object.task_set.select_related("role", "event").order_by(
                    "-event__slug"
                ),
                "award_form": AwardForm(form_tag=False, prefix="award", **kwargs),
                "task_form": TaskForm(form_tag=False, prefix="task", **kwargs),
            }
        )
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # remove existing Qualifications for user
        Qualification.objects.filter(person=self.object).delete()
        # add new Qualifications
        for lesson in form.cleaned_data.pop("lessons"):
            Qualification.objects.create(person=self.object, lesson=lesson)
        return super().form_valid(form)


class PersonDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Person
    permission_required = "workshops.delete_person"
    success_url = reverse_lazy("all_persons")
    pk_url_kwarg = "person_id"


class PersonPermissions(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = "workshops.change_person"
    form_class = PersonPermissionsForm
    pk_url_kwarg = "person_id"
    queryset = Person.objects.prefetch_related(
        "groups",
        Prefetch(
            "user_permissions",
            queryset=Permission.objects.select_related("content_type"),
        ),
    )


@login_required
def person_password(request, person_id):
    user = get_object_or_404(Person, pk=person_id)

    # Either the user requests change of their own password, or someone with
    # permission for changing person does.
    if not (
        (request.user == user) or (request.user.has_perm("workshops.change_person"))
    ):
        raise PermissionDenied

    Form = PasswordChangeForm
    if request.user.is_superuser:
        Form = SetPasswordForm
    elif request.user.pk != user.pk:
        # non-superuser can only change their own password, not someone else's
        raise PermissionDenied

    if request.method == "POST":
        form = Form(user, request.POST)
        if form.is_valid():
            form.save()  # saves the password for the user

            update_session_auth_hash(request, form.user)

            messages.success(request, "Password was changed successfully.")

            return redirect(reverse("person_details", args=[user.id]))

        else:
            messages.error(request, "Fix errors below.")
    else:
        form = Form(user)

    form.helper = BootstrapHelper(add_cancel_button=False)
    return render(
        request,
        "generic_form.html",
        {"form": form, "model": Person, "object": user, "title": "Change password"},
    )


@admin_required
@permission_required(
    ["workshops.delete_person", "workshops.change_person"], raise_exception=True
)
def persons_merge(request):
    """Display two persons side by side on GET and merge them on POST.

    If no persons are supplied via GET params, display person selection
    form."""
    obj_a_pk = request.GET.get("person_a")
    obj_b_pk = request.GET.get("person_b")

    if not obj_a_pk or not obj_b_pk:
        context = {
            "title": "Merge Persons",
            "form": PersonsSelectionForm(),
        }
        if "next" in request.GET:
            return redirect(request.GET.get("next", "/"))
        return render(request, "generic_form.html", context)

    elif obj_a_pk == obj_b_pk:
        context = {
            "title": "Merge Persons",
            "form": PersonsSelectionForm(),
        }
        messages.warning(request, "You cannot merge the same person with " "themself.")
        if "next" in request.GET:
            return redirect(request.GET.get("next", "/"))
        return render(request, "generic_form.html", context)

    obj_a = get_object_or_404(Person, pk=obj_a_pk)
    obj_b = get_object_or_404(Person, pk=obj_b_pk)

    form = PersonsMergeForm(initial=dict(person_a=obj_a, person_b=obj_b))

    if request.method == "POST":
        form = PersonsMergeForm(request.POST)

        if form.is_valid():
            # merging in process
            data = form.cleaned_data

            obj_a = data["person_a"]
            obj_b = data["person_b"]

            # `base_obj` stays in the database after merge
            # `merging_obj` will be removed from DB after merge
            if data["id"] == "obj_a":
                base_obj = obj_a
                merging_obj = obj_b
                base_a = True
            else:
                base_obj = obj_b
                merging_obj = obj_a
                base_a = False

            # non-M2M-relationships
            easy = (
                "username",
                "personal",
                "middle",
                "family",
                "email",
                "secondary_email",
                "may_contact",
                "publish_profile",
                "gender",
                "gender_other",
                "airport",
                "github",
                "twitter",
                "url",
                "affiliation",
                "occupation",
                "orcid",
                "is_active",
            )

            # M2M relationships
            difficult = (
                "award_set",
                "qualification_set",
                "domains",
                "languages",
                "task_set",
                "trainingprogress_set",
                "comment_comments",  # made by this person
                "comments",  # made by others regarding this person
            )

            try:
                _, integrity_errors = merge_objects(
                    obj_a, obj_b, easy, difficult, choices=data, base_a=base_a
                )

                if integrity_errors:
                    msg = (
                        "There were integrity errors when merging related "
                        "objects:\n"
                        "\n".join(integrity_errors)
                    )
                    messages.warning(request, msg)

            except ProtectedError as e:
                return failed_to_delete(
                    request, object=merging_obj, protected_objects=e.protected_objects
                )

            else:
                messages.success(
                    request,
                    "Persons were merged successfully. "
                    "You were redirected to the base "
                    "person.",
                )
                return redirect(base_obj.get_absolute_url())
        else:
            messages.error(request, "Fix errors in the form.")

    context = {
        "title": "Merge two persons",
        "form": form,
        "obj_a": obj_a,
        "obj_b": obj_b,
    }
    return render(request, "workshops/persons_merge.html", context)


@admin_required
def sync_usersocialauth(request, person_id):
    person_id = int(person_id)
    try:
        person = Person.objects.get(pk=person_id)
    except Person.DoesNotExist:
        messages.error(
            request,
            "Cannot sync UserSocialAuth table for person #{} "
            "-- there is no Person with such id.".format(person_id),
        )
        return redirect(reverse("persons"))
    else:
        try:
            result = person.synchronize_usersocialauth()
            if result:
                messages.success(
                    request, "Social account was successfully synchronized."
                )
            else:
                messages.error(
                    request,
                    "It was not possible to synchronize this person "
                    "with their social account.",
                )

        except GithubException:
            messages.error(
                request,
                "Cannot sync UserSocialAuth table for person #{} "
                "due to errors with GitHub API.".format(person_id),
            )

        return redirect(reverse("person_details", args=(person_id,)))


# ------------------------------------------------------------


class AllEvents(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_events"
    template_name = "workshops/all_events.html"
    queryset = (
        Event.objects.select_related("assigned_to")
        .prefetch_related("host", "tags")
        .annotate(
            num_instructors=Sum(
                Case(
                    When(task__role__name="instructor", then=Value(1)),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
        )
        .order_by("-start")
    )
    filter_class = EventFilter
    title = "All Events"


@admin_required
def event_details(request, slug):
    """List details of a particular event."""
    try:
        sponsorship_prefetch = Prefetch(
            "sponsorship_set", queryset=Sponsorship.objects.select_related("contact")
        )
        task_prefetch = Prefetch(
            "task_set",
            to_attr="contacts",
            queryset=Task.objects.select_related("person")
            .filter(
                # we only want hosts, organizers and instructors
                Q(role__name="host")
                | Q(role__name="organizer")
                | Q(role__name="instructor")
            )
            .filter(person__may_contact=True)
            .exclude(Q(person__email="") | Q(person__email=None)),
        )
        event = (
            Event.objects.attendance()
            .prefetch_related(sponsorship_prefetch, task_prefetch)
            .select_related(
                "assigned_to",
                "host",
                "administrator",
            )
            .get(slug=slug)
        )
        member_sites = Membership.objects.filter(task__event=event).distinct()
    except Event.DoesNotExist:
        raise Http404("Event matching query does not exist.")

    person_important_badges = Prefetch(
        "person__badges",
        to_attr="important_badges",
        queryset=Badge.objects.filter(name__in=Badge.IMPORTANT_BADGES),
    )

    tasks = (
        Task.objects.filter(event__id=event.id)
        .select_related("event", "person", "role")
        .prefetch_related(person_important_badges)
        .order_by("role__name")
    )

    admin_lookup_form = AdminLookupForm()
    if event.assigned_to:
        admin_lookup_form = AdminLookupForm(initial={"person": event.assigned_to})

    admin_lookup_form.helper = BootstrapHelper(
        form_action=reverse("event_assign", args=[slug]), add_cancel_button=False
    )

    context = {
        "title": "Event {0}".format(event),
        "event": event,
        "tasks": tasks,
        "member_sites": member_sites,
        "all_emails": tasks.filter(person__may_contact=True)
        .exclude(person__email=None)
        .values_list("person__email", flat=True),
        "today": datetime.date.today(),
        "admin_lookup_form": admin_lookup_form,
    }
    return render(request, "workshops/event.html", context)


@admin_required
def validate_event(request, slug):
    """Check the event's home page *or* the specified URL (for testing)."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        raise Http404("Event matching query does not exist.")

    page_url = request.GET.get("url", None)  # for manual override
    if page_url is None:
        page_url = event.url

    page_url = page_url.strip()

    error_messages = []
    warning_messages = []

    try:
        metadata = fetch_workshop_metadata(page_url)
        # validate metadata
        error_messages, warning_messages = validate_workshop_metadata(metadata)

    except WrongWorkshopURL as e:
        error_messages.append(str(e))

    except requests.exceptions.HTTPError as e:
        error_messages.append(
            'Request for "{0}" returned status code {1}'.format(
                page_url, e.response.status_code
            )
        )

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        error_messages.append("Network connection error.")

    context = {
        "title": "Validate Event {0}".format(event),
        "event": event,
        "page": page_url,
        "error_messages": error_messages,
        "warning_messages": warning_messages,
    }
    return render(request, "workshops/validate_event.html", context)


class EventCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView):
    permission_required = "workshops.add_event"
    model = Event
    form_class = EventCreateForm
    template_name = "workshops/event_create_form.html"

    def form_valid(self, form):
        """Additional functions for validating Event Create form:
        * maybe adding a mail job, if conditions are met
        """
        # save the object
        res = super().form_valid(form)

        # check conditions for running a PostWorkshopAction
        if PostWorkshopAction.check(self.object):
            triggers = Trigger.objects.filter(
                active=True, action="week-after-workshop-completion"
            )
            ActionManageMixin.add(
                action_class=PostWorkshopAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object),
                object_=self.object,
                request=self.request,
            )

        # check conditions for running a InstructorsHostIntroductionAction
        if InstructorsHostIntroductionAction.check(self.object):
            triggers = Trigger.objects.filter(
                active=True, action="instructors-host-introduction"
            )
            ActionManageMixin.add(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object),
                object_=self.object,
                request=self.request,
            )

        # return remembered results
        return res


class EventUpdate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView):
    permission_required = [
        "workshops.change_event",
        "workshops.add_task",
        "workshops.add_sponsorship",
    ]
    queryset = Event.objects.select_related(
        "assigned_to",
        "administrator",
        "language",
    ).prefetch_related("sponsorship_set")
    slug_field = "slug"
    template_name = "workshops/event_edit_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kwargs = {
            "initial": {"event": self.object},
            "widgets": {"event": HiddenInput()},
        }
        context.update(
            {
                "tasks": self.get_object()
                .task_set.select_related("person", "role")
                .order_by("role__name"),
                "task_form": TaskForm(form_tag=False, prefix="task", **kwargs),
                "sponsor_form": SponsorshipForm(
                    form_tag=False, prefix="sponsor", **kwargs
                ),
            }
        )
        return context

    def get_form_class(self):
        return partial(EventForm, show_lessons=True, add_comment=True)

    def form_valid(self, form):
        """Check if RQ job conditions changed, and add/delete jobs if
        necessary."""
        old = self.get_object()
        check_pwa_old = PostWorkshopAction.check(old)
        check_ihia_old = InstructorsHostIntroductionAction.check(old)
        check_afwa_old = AskForWebsiteAction.check(old)
        check_rha_old = RecruitHelpersAction.check(old)

        res = super().form_valid(form)
        new = self.object  # refreshed by `super().form_valid()`
        check_pwa_new = PostWorkshopAction.check(new)
        check_ihia_new = InstructorsHostIntroductionAction.check(new)
        check_afwa_new = AskForWebsiteAction.check(new)
        check_rha_new = RecruitHelpersAction.check(new)

        # PostWorkshopAction conditions are not met, but weren't before
        if not check_pwa_old and check_pwa_new:
            triggers = Trigger.objects.filter(
                active=True, action="week-after-workshop-completion"
            )
            ActionManageMixin.add(
                action_class=PostWorkshopAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object),
                object_=self.object,
                request=self.request,
            )

        # PostWorkshopAction conditions were met, but aren't anymore
        elif check_pwa_old and not check_pwa_new:
            jobs = self.object.rq_jobs.filter(
                trigger__action="week-after-workshop-completion"
            )
            ActionManageMixin.remove(
                action_class=PostWorkshopAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object,
                request=self.request,
            )

        # InstructorsHostIntroductionAction conditions are not met, but weren't before
        if not check_ihia_old and check_ihia_new:
            triggers = Trigger.objects.filter(
                active=True, action="instructors-host-introduction"
            )
            ActionManageMixin.add(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object),
                object_=self.object,
                request=self.request,
            )

        # InstructorsHostIntroductionAction conditions were met, but aren't anymore
        elif check_ihia_old and not check_ihia_new:
            jobs = self.object.rq_jobs.filter(
                trigger__action="instructors-host-introduction"
            )
            ActionManageMixin.remove(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object,
                request=self.request,
            )

        # AskForWebsiteAction conditions are met, but weren't before
        if not check_afwa_old and check_afwa_new:
            triggers = Trigger.objects.filter(active=True, action="ask-for-website")
            ActionManageMixin.add(
                action_class=AskForWebsiteAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object),
                object_=self.object,
                request=self.request,
            )

        # AskForWebsiteAction conditions were met, but aren't anymore
        elif check_afwa_old and not check_afwa_new:
            jobs = self.object.rq_jobs.filter(trigger__action="ask-for-website")
            ActionManageMixin.remove(
                action_class=AskForWebsiteAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object,
                request=self.request,
            )

        # RecruitHelpersAction conditions are met, but weren't before
        if not check_rha_old and check_rha_new:
            triggers = Trigger.objects.filter(active=True, action="recruit-helpers")
            ActionManageMixin.add(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object),
                object_=self.object,
                request=self.request,
            )

        # RecruitHelpersAction conditions were met, but aren't anymore
        elif check_rha_old and not check_rha_new:
            jobs = self.object.rq_jobs.filter(trigger__action="recruit-helpers")
            ActionManageMixin.remove(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object,
                request=self.request,
            )

        return res


class EventDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Event
    permission_required = "workshops.delete_event"
    success_url = reverse_lazy("all_events")

    def before_delete(self, *args, **kwargs):
        jobs = self.object.rq_jobs.filter(
            trigger__action="week-after-workshop-completion"
        )
        ActionManageMixin.remove(
            action_class=PostWorkshopAction,
            logger=logger,
            scheduler=scheduler,
            connection=redis_connection,
            jobs=jobs.values_list("job_id", flat=True),
            object_=self.object,
            request=self.request,
        )

        jobs = self.object.rq_jobs.filter(
            trigger__action="instructors-host-introduction"
        )
        ActionManageMixin.remove(
            action_class=InstructorsHostIntroductionAction,
            logger=logger,
            scheduler=scheduler,
            connection=redis_connection,
            jobs=jobs.values_list("job_id", flat=True),
            object_=self.object,
            request=self.request,
        )

        # This should not happen - first one would have to remove related instructor
        # task, therefore cancelling the job, which would render this part pointless.
        jobs = self.object.rq_jobs.filter(trigger__action="ask-for-website")
        ActionManageMixin.remove(
            action_class=AskForWebsiteAction,
            logger=logger,
            scheduler=scheduler,
            connection=redis_connection,
            jobs=jobs.values_list("job_id", flat=True),
            object_=self.object,
            request=self.request,
        )

        jobs = self.object.rq_jobs.filter(trigger__action="recruit-helpers")
        ActionManageMixin.remove(
            action_class=RecruitHelpersAction,
            logger=logger,
            scheduler=scheduler,
            connection=redis_connection,
            jobs=jobs.values_list("job_id", flat=True),
            object_=self.object,
            request=self.request,
        )


@admin_required
def event_import(request):
    """Read metadata from remote URL and return them as JSON.

    This is used to read metadata from workshop website and then fill up fields
    on event_create form."""

    url = request.GET.get("url", "").strip()

    try:
        metadata = fetch_workshop_metadata(url)
        # normalize the metadata
        metadata = parse_workshop_metadata(metadata)
        return JsonResponse(metadata)

    except requests.exceptions.HTTPError as e:
        return HttpResponseBadRequest(
            'Request for "{0}" returned status code {1}.'.format(
                url, e.response.status_code
            )
        )

    except requests.exceptions.RequestException:
        return HttpResponseBadRequest("Network connection error.")

    except WrongWorkshopURL as e:
        return HttpResponseBadRequest(str(e))

    except KeyError:
        return HttpResponseBadRequest('Missing or wrong "url" parameter.')


class EventAssign(OnlyForAdminsMixin, AssignView):
    permission_required = "workshops.change_event"
    model = Event
    pk_url_kwarg = "request_id"
    person_url_kwarg = "person_id"


@admin_required
@permission_required(
    ["workshops.delete_event", "workshops.change_event"], raise_exception=True
)
def events_merge(request):
    """Display two events side by side on GET and merge them on POST.

    If no events are supplied via GET params, display event selection form."""
    obj_a_pk = request.GET.get("event_a")
    obj_b_pk = request.GET.get("event_b")

    if not obj_a_pk and not obj_b_pk:
        context = {
            "title": "Merge Events",
            "form": EventsSelectionForm(),
        }
        return render(request, "generic_form.html", context)

    obj_a = get_object_or_404(Event, pk=obj_a_pk)
    obj_b = get_object_or_404(Event, pk=obj_b_pk)

    form = EventsMergeForm(initial=dict(event_a=obj_a, event_b=obj_b))

    if request.method == "POST":
        form = EventsMergeForm(request.POST)

        if form.is_valid():
            # merging in process
            data = form.cleaned_data

            obj_a = data["event_a"]
            obj_b = data["event_b"]

            # `base_obj` stays in the database after merge
            # `merging_obj` will be removed from DB after merge
            if data["id"] == "obj_a":
                base_obj = obj_a
                merging_obj = obj_b
                base_a = True
            else:
                base_obj = obj_b
                merging_obj = obj_a
                base_a = False

            # non-M2M-relationships:
            easy = (
                "slug",
                "completed",
                "assigned_to",
                "start",
                "end",
                "host",
                "administrator",
                "url",
                "language",
                "reg_key",
                "admin_fee",
                "attendance",
                "contact",
                "country",
                "venue",
                "address",
                "latitude",
                "longitude",
                "learners_pre",
                "learners_post",
                "instructors_pre",
                "instructors_post",
                "learners_longterm",
            )
            # M2M relationships
            difficult = ("tags", "task_set")

            try:
                _, integrity_errors = merge_objects(
                    obj_a, obj_b, easy, difficult, choices=data, base_a=base_a
                )

                if integrity_errors:
                    msg = (
                        "There were integrity errors when merging related "
                        "objects:\n"
                        "\n".join(integrity_errors)
                    )
                    messages.warning(request, msg)

            except ProtectedError as e:
                return failed_to_delete(
                    request, object=merging_obj, protected_objects=e.protected_objects
                )

            else:
                messages.success(
                    request,
                    "Events were merged successfully. "
                    "You were redirected to the base "
                    "event.",
                )
                return redirect(base_obj.get_absolute_url())
        else:
            messages.error(request, "Fix errors in the form.")

    context = {
        "title": "Merge two events",
        "obj_a": obj_a,
        "obj_b": obj_b,
        "form": form,
    }
    return render(request, "workshops/events_merge.html", context)


@admin_required
def events_metadata_changed(request):
    """List events with metadata changed."""
    events = Event.objects.active().filter(metadata_changed=True)

    assigned_to, is_admin = assignment_selection(request)

    if assigned_to == "me":
        events = events.filter(assigned_to=request.user)

    elif assigned_to == "noone":
        events = events.filter(assigned_to=None)

    elif assigned_to == "all":
        # no filtering
        pass

    else:
        # no filtering
        pass

    context = {
        "title": "Events with metadata changed",
        "events": events,
        "is_admin": is_admin,
        "assigned_to": assigned_to,
    }
    return render(request, "workshops/events_metadata_changed.html", context)


@admin_required
@permission_required("workshops.change_event", raise_exception=True)
def event_review_metadata_changes(request, slug):
    """Review changes made to metadata on event's website."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        raise Http404("No event found matching the query.")

    try:
        metadata = fetch_workshop_metadata(event.website_url)
    except requests.exceptions.RequestException:
        messages.error(
            request,
            "There was an error while fetching event's "
            "website. Make sure the event has website URL "
            "provided, and that it's reachable.",
        )
        return redirect(event.get_absolute_url())

    metadata = parse_workshop_metadata(metadata)

    # save serialized metadata in session so in case of acceptance we don't
    # reload them
    cmd = WebsiteUpdatesCommand()
    metadata_serialized = cmd.serialize(metadata)
    request.session["metadata_from_event_website"] = metadata_serialized

    context = {
        "title": "Review changes for {}".format(str(event)),
        "metadata": metadata,
        "event": event,
    }
    return render(request, "workshops/event_review_metadata_changes.html", context)


@admin_required
@permission_required("workshops.change_event", raise_exception=True)
def event_accept_metadata_changes(request, slug):
    """Review changes made to metadata on event's website."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        raise Http404("No event found matching the query.")

    # load serialized metadata from session
    metadata_serialized = request.session.get("metadata_from_event_website")
    if not metadata_serialized:
        raise Http404("Nothing to update.")
    cmd = WebsiteUpdatesCommand()
    metadata = cmd.deserialize(metadata_serialized)

    # update values
    ALLOWED_METADATA = (
        "start",
        "end",
        "country",
        "venue",
        "address",
        "latitude",
        "longitude",
        "contact",
        "reg_key",
    )
    for key, value in metadata.items():
        if hasattr(event, key) and key in ALLOWED_METADATA:
            setattr(event, key, value)

    # update instructors and helpers
    instructors = ", ".join(metadata.get("instructors", []))
    helpers = ", ".join(metadata.get("helpers", []))
    comment_txt = "INSTRUCTORS: {}\n\nHELPERS: {}".format(instructors, helpers)
    add_comment(event, comment_txt)

    # save serialized metadata
    event.repository_metadata = metadata_serialized

    # dismiss notification
    event.metadata_all_changes = ""
    event.metadata_changed = False
    event.save()

    # remove metadata from session
    del request.session["metadata_from_event_website"]

    messages.success(request, "Successfully updated {}.".format(event.slug))

    return redirect(reverse("event_details", args=[event.slug]))


@admin_required
@permission_required("workshops.change_event", raise_exception=True)
def event_dismiss_metadata_changes(request, slug):
    """Review changes made to metadata on event's website."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        raise Http404("No event found matching the query.")

    # dismiss notification
    event.metadata_all_changes = ""
    event.metadata_changed = False
    event.save()

    # remove metadata from session
    if "metadata_from_event_website" in request.session:
        del request.session["metadata_from_event_website"]

    messages.success(request, "Changes to {} were dismissed.".format(event.slug))

    return redirect(reverse("event_details", args=[event.slug]))


# ------------------------------------------------------------


class AllTasks(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_tasks"
    template_name = "workshops/all_tasks.html"
    filter_class = TaskFilter
    queryset = Task.objects.select_related("event", "person", "role")
    title = "All Tasks"


class TaskDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = Task.objects.all()
    context_object_name = "task"
    pk_url_kwarg = "task_id"
    template_name = "workshops/task.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Task {0}".format(self.object)
        return context


class TaskCreate(
    OnlyForAdminsMixin, PermissionRequiredMixin, RedirectSupportMixin, AMYCreateView,
):
    permission_required = "workshops.add_task"
    model = Task
    form_class = TaskForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"prefix": "task"})
        return kwargs

    def post(self, request, *args, **kwargs):
        """Save request in `self.request`."""
        self.request = request
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        """Additional functions for validating Task Create form:

        * checking membership seats, availability
        * maybe adding a mail job, if conditions are met
        """

        seat_membership = form.cleaned_data["seat_membership"]
        event = form.cleaned_data["event"]
        check_ihia_old = InstructorsHostIntroductionAction.check(event)
        check_afwa_old = AskForWebsiteAction.check(event)
        check_rha_old = RecruitHelpersAction.check(event)

        # check associated membership remaining seats and validity
        if hasattr(self, "request") and seat_membership is not None:
            # check number of available seats
            if seat_membership.seats_instructor_training_remaining == 1:
                messages.warning(
                    self.request,
                    'Membership "{}" has 0 instructor training seats'
                    " available.".format(str(seat_membership)),
                )
            if seat_membership.seats_instructor_training_remaining < 1:
                messages.warning(
                    self.request,
                    'Membership "{}" is using more training seats'
                    " than it's been allowed.".format(str(seat_membership)),
                )

            today = datetime.date.today()
            # check if membership is active
            if not (
                seat_membership.agreement_start
                <= today
                <= seat_membership.agreement_end
            ):
                messages.warning(
                    self.request,
                    'Membership "{}" is not active.'.format(str(seat_membership)),
                )

            # show warning if training falls out of agreement dates
            if (
                event.start
                and event.start < seat_membership.agreement_start
                or event.end
                and event.end > seat_membership.agreement_end
            ):
                messages.warning(
                    self.request,
                    'Training "{}" has start or end date outside '
                    'membership "{}" agreement dates.'.format(
                        str(event), str(seat_membership),
                    ),
                )

        # save the object
        res = super().form_valid(form)

        # check conditions for running a NewInstructorAction
        if NewInstructorAction.check(self.object):
            ActionManageMixin.add(
                action_class=NewInstructorAction,
                logger=logger,
                scheduler=scheduler,
                triggers=Trigger.objects.filter(active=True, action="new-instructor"),
                context_objects=dict(task=self.object, event=self.object.event),
                object_=self.object,
                request=self.request,
            )

        # check conditions for running a NewSupportingInstructorAction
        if NewSupportingInstructorAction.check(self.object):
            ActionManageMixin.add(
                action_class=NewSupportingInstructorAction,
                logger=logger,
                scheduler=scheduler,
                triggers=Trigger.objects.filter(
                    active=True, action="new-supporting-instructor"
                ),
                context_objects=dict(task=self.object, event=self.object.event),
                object_=self.object,
                request=self.request,
            )

        # check conditions for running a InstructorsHostIntroductionAction
        if (
            not check_ihia_old
            and InstructorsHostIntroductionAction.check(self.object.event)
        ):
            triggers = Trigger.objects.filter(
                active=True, action="instructors-host-introduction"
            )
            ActionManageMixin.add(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object.event),
                object_=self.object.event,
                request=self.request,
            )

        # check conditions for running an AskForWebsiteAction
        if (
            not check_afwa_old
            and AskForWebsiteAction.check(self.object.event)
        ):
            triggers = Trigger.objects.filter(active=True, action="ask-for-website")
            ActionManageMixin.add(
                action_class=AskForWebsiteAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object.event),
                object_=self.object.event,
                request=self.request,
            )

        # check conditions for running a RecruitHelpersAction
        if (
            not check_rha_old
            and RecruitHelpersAction.check(self.object.event)
        ):
            triggers = Trigger.objects.filter(active=True, action="recruit-helpers")
            ActionManageMixin.add(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object.event),
                object_=self.object.event,
                request=self.request,
            )

        # When someone adds a helper, then the condition will no longer be met and we
        # have to remove the job.
        elif (
            check_rha_old
            and not RecruitHelpersAction.check(self.object.event)
        ):
            jobs = self.object.event.rq_jobs.filter(trigger__action="recruit-helpers")
            ActionManageMixin.remove(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object.event,
                request=self.request,
            )

        # return remembered results
        return res


class TaskUpdate(
    OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView,
):
    permission_required = "workshops.change_task"
    model = Task
    queryset = Task.objects.select_related("event", "role", "person")
    form_class = TaskForm
    pk_url_kwarg = "task_id"

    def form_valid(self, form):
        """Check if RQ job conditions changed, and add/delete jobs if
        necessary."""
        old = self.get_object()
        check_nia_old = NewInstructorAction.check(old)
        check_nsia_old = NewSupportingInstructorAction.check(old)
        check_ihia_old = InstructorsHostIntroductionAction.check(old.event)
        check_afwa_old = AskForWebsiteAction.check(old.event)
        check_rha_old = RecruitHelpersAction.check(old.event)

        res = super().form_valid(form)
        new = self.object  # refreshed by `super().form_valid()`
        check_nia_new = NewInstructorAction.check(new)
        check_nsia_new = NewSupportingInstructorAction.check(new)
        check_ihia_new = InstructorsHostIntroductionAction.check(new.event)
        check_afwa_new = AskForWebsiteAction.check(new.event)
        check_rha_new = RecruitHelpersAction.check(new.event)

        # NewInstructorAction conditions are met, but weren't before
        if not check_nia_old and check_nia_new:
            triggers = Trigger.objects.filter(active=True, action="new-instructor")
            ActionManageMixin.add(
                action_class=NewInstructorAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(task=self.object, event=self.object.event),
                object_=self.object,
                request=self.request,
            )

        # NewInstructorAction conditions were met, but aren't anymore
        elif check_nia_old and not check_nia_new:
            jobs = self.object.rq_jobs.filter(trigger__action="new-instructor")
            ActionManageMixin.remove(
                action_class=NewInstructorAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object,
                request=self.request,
            )

        # NewSupportingInstructorAction conditions are met, but weren't before
        if not check_nsia_old and check_nsia_new:
            triggers = Trigger.objects.filter(
                active=True, action="new-supporting-instructor"
            )
            ActionManageMixin.add(
                action_class=NewSupportingInstructorAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(task=self.object, event=self.object.event),
                object_=self.object,
                request=self.request,
            )

        # NewSupportingInstructorAction conditions were met, but aren't anymore
        elif check_nsia_old and not check_nsia_new:
            jobs = self.object.rq_jobs.filter(
                trigger__action="new-supporting-instructor"
            )
            ActionManageMixin.remove(
                action_class=NewSupportingInstructorAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object,
                request=self.request,
            )

        # InstructorsHostIntroductionAction conditions are met, but weren't before
        if not check_ihia_old and check_ihia_new:
            triggers = Trigger.objects.filter(
                active=True, action="instructors-host-introduction"
            )
            ActionManageMixin.add(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object.event),
                object_=self.object.event,
                request=self.request,
            )

        # InstructorsHostIntroductionAction conditions were met, but aren't anymore
        elif check_ihia_old and not check_ihia_new:
            jobs = self.object.event.rq_jobs.filter(
                trigger__action="instructors-host-introduction"
            )
            ActionManageMixin.remove(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object.event,
                request=self.request,
            )

        # AskForWebsiteAction conditions are met, but weren't before
        if not check_afwa_old and check_afwa_new:
            triggers = Trigger.objects.filter(active=True, action="ask-for-website")
            ActionManageMixin.add(
                action_class=AskForWebsiteAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object.event),
                object_=self.object.event,
                request=self.request,
            )

        # AskForWebsiteAction conditions were met, but aren't anymore
        elif check_afwa_old and not check_afwa_new:
            jobs = self.object.event.rq_jobs.filter(trigger__action="ask-for-website")
            ActionManageMixin.remove(
                action_class=AskForWebsiteAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object.event,
                request=self.request,
            )

        # RecruitHelpersAction conditions are met, but weren't before
        if not check_rha_old and check_rha_new:
            triggers = Trigger.objects.filter(active=True, action="recruit-helpers")
            ActionManageMixin.add(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.object.event),
                object_=self.object.event,
                request=self.request,
            )

        # RecruitHelpersAction conditions were met, but aren't anymore
        elif check_rha_old and not check_rha_new:
            jobs = self.object.event.rq_jobs.filter(trigger__action="recruit-helpers")
            ActionManageMixin.remove(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object.event,
                request=self.request,
            )

        return res


class TaskDelete(
    OnlyForAdminsMixin, PermissionRequiredMixin, RedirectSupportMixin, AMYDeleteView,
):
    model = Task
    permission_required = "workshops.delete_task"
    success_url = reverse_lazy("all_tasks")
    pk_url_kwarg = "task_id"

    def before_delete(self, *args, **kwargs):
        jobs = self.object.rq_jobs.filter(trigger__action="new-instructor")
        ActionManageMixin.remove(
            action_class=NewInstructorAction,
            logger=logger,
            scheduler=scheduler,
            connection=redis_connection,
            jobs=jobs.values_list("job_id", flat=True),
            object_=self.object,
            request=self.request,
        )

        jobs = self.object.rq_jobs.filter(trigger__action="new-supporting-instructor")
        ActionManageMixin.remove(
            action_class=NewSupportingInstructorAction,
            logger=logger,
            scheduler=scheduler,
            connection=redis_connection,
            jobs=jobs.values_list("job_id", flat=True),
            object_=self.object,
            request=self.request,
        )

        # We need to store the check from before object delete
        # and compare in the `after_delete` method.
        old = self.get_object()
        self.event = old.event
        self.check_ihia_old = InstructorsHostIntroductionAction.check(self.event)
        self.check_afwa_old = AskForWebsiteAction.check(self.event)
        self.check_rha_old = RecruitHelpersAction.check(self.event)

    def after_delete(self, *args, **kwargs):
        self.check_ihia_new = InstructorsHostIntroductionAction.check(self.event)
        self.check_afwa_new = AskForWebsiteAction.check(self.event)
        self.check_rha_new = RecruitHelpersAction.check(self.event)

        # InstructorsHostIntroductionAction conditions were met, but aren't anymore
        if self.check_ihia_old and not self.check_ihia_new:
            jobs = self.object.event.rq_jobs.filter(
                trigger__action="instructors-host-introduction"
            )
            ActionManageMixin.remove(
                action_class=InstructorsHostIntroductionAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object.event,
                request=self.request,
            )

        # AskForWebsiteAction conditions were met, but aren't anymore
        if self.check_afwa_old and not self.check_afwa_new:
            jobs = self.object.event.rq_jobs.filter(
                trigger__action="ask-for-website"
            )
            ActionManageMixin.remove(
                action_class=AskForWebsiteAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.object.event,
                request=self.request,
            )

        # RecruitHelpersAction conditions are met, but weren't before
        if not self.check_rha_old and self.check_rha_new:
            triggers = Trigger.objects.filter(active=True, action="recruit-helpers")
            ActionManageMixin.add(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                triggers=triggers,
                context_objects=dict(event=self.event),
                object_=self.event,
                request=self.request,
            )

        # RecruitHelpersAction conditions were met, but aren't anymore
        elif self.check_rha_old and not self.check_rha_new:
            jobs = self.object.event.rq_jobs.filter(trigger__action="recruit-helpers")
            ActionManageMixin.remove(
                action_class=RecruitHelpersAction,
                logger=logger,
                scheduler=scheduler,
                connection=redis_connection,
                jobs=jobs.values_list("job_id", flat=True),
                object_=self.event,
                request=self.request,
            )


# ------------------------------------------------------------


class MockAwardCreate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    PrepopulationSupportMixin,
    AMYCreateView,
):
    permission_required = "workshops.add_award"
    model = Award
    form_class = AwardForm
    populate_fields = ["badge", "person"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"prefix": "award"})
        return kwargs

    def get_initial(self, **kwargs):
        initial = super().get_initial(**kwargs)

        # Determine initial event in AwardForm
        if "find-training" in self.request.GET:
            tasks = Person.objects.get(
                pk=self.request.GET["person"]
            ).get_training_tasks()
            if tasks.count() == 1:
                initial.update({"event": tasks[0].event})

        return initial

    def get_success_url(self):
        return reverse("badge_details", args=[self.object.badge.name])


class AwardCreate(RedirectSupportMixin, MockAwardCreate):
    pass


class MockAwardDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView):
    model = Award
    permission_required = "workshops.delete_award"

    def get_success_url(self):
        return reverse("badge_details", args=[self.get_object().badge.name])


class AwardDelete(RedirectSupportMixin, MockAwardDelete):
    # Modify the MRO to look like:
    # AwardDelete < RedirectSupportMixin < MockAwardDelete
    #
    # This ensures that `super()` when called from `get_success_url` method of
    # RedirectSupportMixin returns MockAwardDelete
    pass


# ------------------------------------------------------------


class AllBadges(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_badges"
    queryset = Badge.objects.order_by("name").annotate(num_awarded=Count("award"))
    template_name = "workshops/all_badges.html"
    title = "All Badges"


class BadgeDetails(OnlyForAdminsMixin, AMYDetailView):
    queryset = Badge.objects.all()
    context_object_name = "badge"
    template_name = "workshops/badge.html"
    slug_field = "name"
    slug_url_kwarg = "badge_name"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["title"] = "Badge {0}".format(self.object)
        filter = BadgeAwardsFilter(
            self.request.GET,
            queryset=self.object.award_set.select_related("event", "person", "badge"),
        )
        context["filter"] = filter

        awards = get_pagination_items(self.request, filter.qs)
        context["awards"] = awards

        return context


# ------------------------------------------------------------


def _workshop_staff_query(lat=None, lng=None):
    """This query is used in two views: workshop staff searching and its CSV
    results. Thanks to factoring-out this function, we're now quite certain
    that the results in both of the views are the same."""
    TTT = Tag.objects.get(name="TTT")
    stalled = Tag.objects.get(name="stalled")
    learner = Role.objects.get(name="learner")
    important_badges = Badge.objects.filter(name__in=Badge.IMPORTANT_BADGES)

    trainee_tasks = (
        Task.objects.filter(event__tags=TTT, role=learner)
        .exclude(event__tags=stalled)
        .exclude(person__badges__in=important_badges)
    )

    # we need to count number of specific roles users had
    # and if they are SWC/DC/LC instructors
    people = (
        Person.objects.filter(airport__isnull=False)
        .select_related("airport")
        .annotate(
            num_taught=Count(
                Case(
                    When(task__role__name="instructor", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
            num_helper=Count(
                Case(
                    When(task__role__name="helper", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
            num_organizer=Count(
                Case(
                    When(task__role__name="organizer", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
            is_trainee=Count("task", filter=(Q(task__in=trainee_tasks))),
            is_trainer=Count("badges", filter=(Q(badges__name="trainer"))),
        )
        .prefetch_related(
            "lessons",
            Prefetch(
                "badges",
                to_attr="important_badges",
                queryset=Badge.objects.filter(name__in=Badge.IMPORTANT_BADGES),
            ),
        )
        .order_by("family", "personal")
    )

    if lat and lng:
        # using Euclidean distance just because it's faster and easier
        complex_F = (F("airport__latitude") - lat) ** 2 + (
            F("airport__longitude") - lng
        ) ** 2
        people = people.annotate(distance=complex_F).order_by("distance", "family")

    return people


@admin_required
def workshop_staff(request):
    """Search for workshop staff."""

    # read data from form, if it was submitted correctly
    lat, lng = None, None
    lessons = list()
    form = WorkshopStaffForm(request.GET)
    if form.is_valid():
        # to highlight (in template) what lessons people know
        lessons = form.cleaned_data["lessons"]

        if form.cleaned_data["airport"]:
            lat = form.cleaned_data["airport"].latitude
            lng = form.cleaned_data["airport"].longitude

        elif form.cleaned_data["latitude"] and form.cleaned_data["longitude"]:
            lat = form.cleaned_data["latitude"]
            lng = form.cleaned_data["longitude"]

    # prepare the query
    people = _workshop_staff_query(lat, lng)

    # filter the query
    f = WorkshopStaffFilter(request.GET, queryset=people)
    people = get_pagination_items(request, f.qs)

    context = {
        "title": "Find Workshop Staff",
        "filter_form": form,
        "persons": people,
        "lessons": lessons,
    }
    return render(request, "workshops/workshop_staff.html", context)


@admin_required
def workshop_staff_csv(request):
    """Generate CSV of workshop staff search results."""

    # read data from form, if it was submitted correctly
    lat, lng = None, None
    form = WorkshopStaffForm(request.GET)
    if form.is_valid():
        if form.cleaned_data["airport"]:
            lat = form.cleaned_data["airport"].latitude
            lng = form.cleaned_data["airport"].longitude

        elif form.cleaned_data["latitude"] and form.cleaned_data["longitude"]:
            lat = form.cleaned_data["latitude"]
            lng = form.cleaned_data["longitude"]

    # prepare the query
    people = _workshop_staff_query(lat, lng)

    # filter the query
    f = WorkshopStaffFilter(request.GET, queryset=people)
    people = f.qs

    # first row of the CSV output
    header_row = (
        "Name",
        "Email",
        "Some badges",
        "Has Trainer badge",
        "Taught times",
        "Is trainee",
        "Airport",
        "Country",
        "Lessons",
        "Affiliation",
    )

    # CSV http header
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; " 'filename="WorkshopStaff.csv"'
    # CSV output
    writer = csv.writer(response)
    writer.writerow(header_row)
    for person in people:
        writer.writerow(
            [
                person.full_name,
                person.email,
                " ".join([badge.name for badge in person.important_badges]),
                "yes" if person.is_trainer else "no",
                person.num_taught,
                "yes" if person.is_trainee else "no",
                str(person.airport) if person.airport else "",
                person.country.name if person.country else "",
                " ".join([lesson.name for lesson in person.lessons.all()]),
                person.affiliation or "",
            ]
        )
    return response


# ------------------------------------------------------------


@csrf_exempt
@admin_required
def search(request):
    """Search the database by term."""

    term = ""
    organizations = events = persons = airports = training_requests = None
    comments = None

    if request.method == "GET" and "term" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            term = form.cleaned_data["term"]
            tokens = re.split(r"\s+", term)
            results = list()

            if form.cleaned_data["in_organizations"]:
                organizations = Organization.objects.filter(
                    Q(domain__icontains=term) | Q(fullname__icontains=term)
                ).order_by("fullname")
                results += list(organizations)

            if form.cleaned_data["in_events"]:
                events = Event.objects.filter(
                    Q(slug__icontains=term)
                    | Q(host__domain__icontains=term)
                    | Q(host__fullname__icontains=term)
                    | Q(url__icontains=term)
                    | Q(contact__icontains=term)
                    | Q(venue__icontains=term)
                    | Q(address__icontains=term)
                ).order_by("-slug")
                results += list(events)

            if form.cleaned_data["in_persons"]:
                # if user searches for two words, assume they mean a person
                # name
                if len(tokens) == 2:
                    name1, name2 = tokens
                    complex_q = (
                        (Q(personal__icontains=name1) & Q(family__icontains=name2))
                        | (Q(personal__icontains=name2) & Q(family__icontains=name1))
                        | Q(email__icontains=term)
                        | Q(secondary_email__icontains=term)
                        | Q(github__icontains=term)
                    )
                    persons = Person.objects.filter(complex_q)
                else:
                    persons = Person.objects.filter(
                        Q(personal__icontains=term)
                        | Q(family__icontains=term)
                        | Q(email__icontains=term)
                        | Q(secondary_email__icontains=term)
                        | Q(github__icontains=term)
                    ).order_by("family")
                results += list(persons)

            if form.cleaned_data["in_airports"]:
                airports = Airport.objects.filter(
                    Q(iata__icontains=term) | Q(fullname__icontains=term)
                ).order_by("iata")
                results += list(airports)

            if form.cleaned_data["in_training_requests"]:
                training_requests = TrainingRequest.objects.filter(
                    Q(group_name__icontains=term)
                    | Q(family__icontains=term)
                    | Q(email__icontains=term)
                    | Q(github__icontains=term)
                    | Q(affiliation__icontains=term)
                    | Q(location__icontains=term)
                    | Q(user_notes__icontains=term)
                )
                results += list(training_requests)

            if form.cleaned_data["in_comments"]:
                comments = Comment.objects.filter(
                    Q(comment__icontains=term)
                    | Q(user_name__icontains=term)
                    | Q(user_email__icontains=term)
                    | Q(user__personal__icontains=term)
                    | Q(user__family__icontains=term)
                    | Q(user__email__icontains=term)
                    | Q(user__github__icontains=term)
                ).prefetch_related("content_object")
                results += list(comments)

            # only 1 record found? Let's move to it immediately
            if len(results) == 1:
                result = results[0]
                if isinstance(result, Comment):
                    return redirect(
                        result.content_object.get_absolute_url()
                        + "#c{}".format(result.id)
                    )
                else:
                    return redirect(result.get_absolute_url())

        else:
            messages.error(request, "Fix errors below.")

    # if empty GET, we'll create a blank form
    else:
        form = SearchForm()

    context = {
        "title": "Search",
        "form": form,
        "term": term,
        "organizations": organizations,
        "events": events,
        "persons": persons,
        "airports": airports,
        "comments": comments,
        "training_requests": training_requests,
    }
    return render(request, "workshops/search.html", context)


# ------------------------------------------------------------


@admin_required
def object_changes(request, version_id):
    """This view is highly inspired by `HistoryCompareDetailView` from
    `django-reversion-compare`:

    https://github.com/jedie/django-reversion-compare/blob/master/reversion_compare/views.py

    The biggest change between above and this code is model-agnosticism:
    the only thing that matters is `version_id` view parameter and underlying
    object. This is where current and previous versions of the object are taken
    from. Only later they're replaced with GET-provided arguments `version1`
    and `version2`."""

    # retrieve object from version/revision
    current_version = get_object_or_404(Version, pk=version_id)
    obj = current_version.object

    # retrieve previous version
    try:
        previous_version = Version.objects.get_for_object(obj).filter(
            pk__lt=current_version.pk
        )[0]
    except IndexError:
        # first revision for an object
        previous_version = current_version

    # set default versions displayed in the template
    version2 = current_version
    version1 = previous_version

    # set default ordering: latest first
    history_latest_first = True

    def _order(queryset):
        """Applies the correct ordering to the given version queryset."""
        return queryset.order_by("-pk" if history_latest_first else "pk")

    # get action list
    action_list = [
        {"version": version, "revision": version.revision}
        for version in _order(
            Version.objects.get_for_object(obj).select_related("revision__user")
        )
    ]

    if len(action_list) >= 2:
        # this preselects radio buttons
        if history_latest_first:
            action_list[0]["first"] = True
            action_list[1]["second"] = True
        else:
            action_list[-1]["first"] = True
            action_list[-2]["second"] = True

    if request.GET:
        form = SelectDiffForm(request.GET)
        if form.is_valid():
            version_id1 = form.cleaned_data["version_id1"]
            version_id2 = form.cleaned_data["version_id2"]

            if version_id1 > version_id2:
                # Compare always the newest one (#2) with the older one (#1)
                version_id1, version_id2 = version_id2, version_id1

            queryset = Version.objects.get_for_object(obj)
            version1 = get_object_or_404(queryset, pk=version_id1)
            version2 = get_object_or_404(queryset, pk=version_id2)
        else:
            messages.warning(request, "Wrong version IDs.")

    context = {
        "title": str(obj),
        "verbose_name": obj._meta.verbose_name,
        "object": obj,
        "version1": version1,
        "version2": version2,
        "revision": version2.revision,
        "fields": [f for f in obj._meta.get_fields() if f.concrete],
        "action": "",
        "compare_view": True,
        "action_list": action_list,
        "comparable": len(action_list) >= 2,
    }
    return render(request, "workshops/object_diff.html", context)


# ------------------------------------------------------------
# "Action required" views


@login_required
def action_required_privacy(request):
    person = request.user

    # disable the view for users who already agreed
    if person.data_privacy_agreement:
        raise Http404("This view is disabled.")

    form = ActionRequiredPrivacyForm(instance=person)

    if request.method == "POST":
        form = ActionRequiredPrivacyForm(request.POST, instance=person)

        if form.is_valid() and form.instance == person:
            person = form.save()
            messages.success(request, "Agreement successfully saved.")

            if "next" in request.GET:
                return redirect(request.GET["next"])
            else:
                return redirect(reverse("dispatch"))
        else:
            messages.error(request, "Fix errors below.")

    context = {
        "title": "Action required: privacy policy agreement",
        "form": form,
    }
    return render(request, "workshops/action_required_privacy.html", context)
