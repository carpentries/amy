import csv
import datetime
import io
import logging
from functools import partial
from typing import Annotated, Any, TypedDict, cast

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.models import Permission
from django.contrib.auth.views import logout_then_login
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError
from django.db.models import (
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Prefetch,
    ProtectedError,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.forms import HiddenInput
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django_stubs_ext import Annotations
from flags.state import flag_enabled  # type: ignore[import-untyped]
from github.GithubException import GithubException
from reversion.models import Revision, Version
from reversion_compare.forms import SelectDiffForm

from src.communityroles.forms import CommunityRoleForm
from src.communityroles.models import CommunityRole, CommunityRoleConfig
from src.consents.forms import ActiveTermConsentsForm
from src.consents.models import Consent, TermEnum, TermOptionChoices
from src.dashboard.forms import AssignmentForm
from src.emails.actions.ask_for_website import (
    ask_for_website_strategy,
    run_ask_for_website_strategy,
)
from src.emails.actions.exceptions import EmailStrategyException
from src.emails.actions.host_instructors_introduction import (
    host_instructors_introduction_strategy,
    run_host_instructors_introduction_strategy,
)
from src.emails.actions.instructor_badge_awarded import (
    instructor_badge_awarded_strategy,
    run_instructor_badge_awarded_strategy,
)
from src.emails.actions.instructor_task_created_for_workshop import (
    instructor_task_created_for_workshop_strategy,
    run_instructor_task_created_for_workshop_strategy,
)
from src.emails.actions.instructor_training_approaching import (
    instructor_training_approaching_strategy,
    run_instructor_training_approaching_strategy,
)
from src.emails.actions.instructor_training_completed_not_badged import (
    instructor_training_completed_not_badged_strategy,
    run_instructor_training_completed_not_badged_strategy,
)
from src.emails.actions.membership_quarterly_emails import (
    membership_quarterly_email_strategy,
    run_membership_quarterly_email_strategy,
    update_context_json_and_to_header_json,
)
from src.emails.actions.post_workshop_7days import (
    post_workshop_7days_strategy,
    run_post_workshop_7days_strategy,
)
from src.emails.actions.recruit_helpers import (
    recruit_helpers_strategy,
    run_recruit_helpers_strategy,
)
from src.emails.signals import (
    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
    persons_merged_signal,
)
from src.fiscal.models import MembershipTask
from src.offering.models import Account
from src.recruitment.models import InstructorRecruitmentSignup
from src.workshops.base_forms import GenericDeleteForm
from src.workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYDetailView,
    AMYListView,
    AMYUpdateView,
    AssignView,
    AuthenticatedHttpRequest,
    PrepopulationSupportMixin,
    RedirectSupportMixin,
)
from src.workshops.consts import IATA_AIRPORTS
from src.workshops.exceptions import InternalError, WrongWorkshopURL
from src.workshops.filters import (
    BadgeAwardsFilter,
    EventFilter,
    PersonFilter,
    TaskFilter,
    WorkshopStaffFilter,
)
from src.workshops.forms import (
    AdminLookupForm,
    AwardForm,
    BootstrapHelper,
    BulkUploadCSVForm,
    EventCreateForm,
    EventForm,
    EventsMergeForm,
    EventsSelectionForm,
    PersonCreateForm,
    PersonForm,
    PersonPermissionsForm,
    PersonsMergeForm,
    PersonsSelectionForm,
    TaskForm,
    WorkshopStaffForm,
)
from src.workshops.models import (
    Award,
    Badge,
    Event,
    Membership,
    Person,
    Qualification,
    Role,
    Tag,
    Task,
    TrainingProgress,
    TrainingRequirement,
)
from src.workshops.signals import create_comment_signal
from src.workshops.utils.access import OnlyForAdminsMixin, admin_required, login_required
from src.workshops.utils.comments import add_comment
from src.workshops.utils.merge import merge_objects
from src.workshops.utils.metadata import (
    fetch_workshop_metadata,
    metadata_deserialize,
    metadata_serialize,
    parse_workshop_metadata,
    validate_workshop_metadata,
)
from src.workshops.utils.pagination import get_pagination_items
from src.workshops.utils.person_upload import (
    PersonTaskEntry,
    create_uploaded_persons_tasks,
    upload_person_task_csv,
    verify_upload_person_task,
)
from src.workshops.utils.urls import safe_next_or_default_url
from src.workshops.utils.usernames import create_username
from src.workshops.utils.views import failed_to_delete

logger = logging.getLogger("amy")


@login_required
def logout_then_login_with_msg(request: AuthenticatedHttpRequest) -> HttpResponse:
    messages.success(request, "You were successfully logged-out.")
    return logout_then_login(request)


@admin_required
def changes_log(request: AuthenticatedHttpRequest) -> HttpResponse:
    log = Revision.objects.all().select_related("user").prefetch_related("version_set").order_by("-date_created")
    log_paginated = get_pagination_items(request, log)
    context = {"log": log_paginated}
    return render(request, "workshops/changes_log.html", context)


# ------------------------------------------------------------

PERSON_HAS_NO_AIRPORT_ALERT = "{person} has no airport information on record."


class AllPersons(OnlyForAdminsMixin, AMYListView[Person]):
    context_object_name = "all_persons"
    template_name = "workshops/all_persons.html"
    filter_class = PersonFilter
    queryset = Person.objects.prefetch_related(
        Prefetch(
            "badges",
            to_attr="important_badges",
            queryset=Badge.objects.filter(name__in=Badge.IMPORTANT_BADGES),
        ),
        Prefetch(
            "communityrole_set",
            to_attr="instructor_community_roles",
            queryset=CommunityRole.objects.filter(config__name="instructor"),
        ),
    )
    title = "All Persons"


class PersonDetails(OnlyForAdminsMixin, AMYDetailView[Person]):
    context_object_name = "person"
    template_name = "workshops/person.html"
    pk_url_kwarg = "person_id"
    queryset = (
        Person.objects.annotate_with_role_count()
        .prefetch_related(
            "badges",
            "lessons",
            "domains",
            "languages",
            Prefetch(
                "award_set",
                queryset=Award.objects.select_related("badge", "event", "awarded_by"),
            ),
            Prefetch(
                "task_set",
                queryset=Task.objects.select_related("role", "event"),
            ),
            Prefetch(
                "task_set",
                to_attr="training_tasks",
                queryset=Task.objects.filter(role__name="learner", event__tags__name="TTT").select_related(
                    "role", "event"
                ),
            ),
            "trainingrequest_set",
            "trainingprogress_set",
            Prefetch(
                "membershiptask_set",
                queryset=MembershipTask.objects.select_related("role", "membership"),
            ),
        )
        .order_by("family", "personal")
    )

    def get_context_data(self, **kwargs: dict[str, Any]) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        title = f"Person {self.object}"
        context["title"] = title

        is_usersocialauth_in_sync = len(self.object.github_usersocialauth) > 0
        context["is_usersocialauth_in_sync"] = is_usersocialauth_in_sync
        consents = Consent.objects.filter(person=self.object).active().select_related("term", "term_option")
        consent_by_description = {consent.term.short_description: consent for consent in consents}
        context["consents"] = consent_by_description
        if not self.object.is_active:
            messages.info(self.request, f"{title} is not active.")
        if not self.object.airport_iata:
            messages.warning(self.request, PERSON_HAS_NO_AIRPORT_ALERT.format(person=title))
        context["account"] = Account.objects.filter(
            generic_relation_content_type=ContentType.objects.get_for_model(Person),
            generic_relation_pk=self.object.pk,
        ).first()
        return context


@admin_required
def person_bulk_add_template(request: AuthenticatedHttpRequest) -> HttpResponse:
    """Dynamically generate a CSV template that can be used to bulk-upload people."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=BulkPersonAddTemplate.csv"

    writer = csv.writer(response)
    writer.writerow(Person.PERSON_TASK_UPLOAD_FIELDS)
    return response


@admin_required
@permission_required(["workshops.add_person", "workshops.change_person"], raise_exception=True)
def person_bulk_add(request: AuthenticatedHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = BulkUploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            request_file = cast(UploadedFile, request.FILES["file"])
            charset = request_file.charset or settings.DEFAULT_CHARSET
            assert request_file.file  # for mypy
            stream = io.TextIOWrapper(request_file.file, charset)
            try:
                persons_tasks, empty_fields = upload_person_task_csv(stream)
            except csv.Error as e:
                messages.error(request, f"Error processing uploaded .CSV file: {e}")
            except UnicodeDecodeError:
                messages.error(request, f"Please provide a file in {charset} encoding.")
            else:
                if empty_fields:
                    msg_template = "The following required fields were not found in the uploaded file: {}"
                    msg = msg_template.format(", ".join(empty_fields))
                    messages.error(request, msg)
                else:
                    # Put everything into session and then redirect to confirmation page which can save the data.
                    request.session["bulk-add-people"] = persons_tasks
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
@permission_required(["workshops.add_person", "workshops.change_person"], raise_exception=True)
def person_bulk_add_confirmation(request: AuthenticatedHttpRequest) -> HttpResponse:
    """
    This view allows for manipulating and saving session-stored upload data.
    """
    persons_tasks: list[PersonTaskEntry] | None = request.session.get("bulk-add-people")
    match = request.session.get("bulk-add-people-match", False)

    # if the session is empty, add message and redirect
    if not persons_tasks:
        messages.warning(request, "Could not locate CSV data, please upload again.")
        return redirect("person_bulk_add")

    if request.method == "POST":
        # update values if user wants to change them
        personals = request.POST.getlist("personal")
        families = request.POST.getlist("family")
        usernames = request.POST.getlist("username")
        emails = request.POST.getlist("email")
        airport_iatas = request.POST.getlist("airport_iata")
        events = request.POST.getlist("event")
        roles = request.POST.getlist("role")
        data_update = zip(personals, families, usernames, emails, airport_iatas, events, roles, strict=False)
        for k, record in enumerate(data_update):
            personal, family, username, email, airport_iata, event, role = record
            existing_person_id = persons_tasks[k].get("existing_person_id")
            persons_tasks[k] = PersonTaskEntry(
                **{
                    "personal": personal,
                    "family": family,
                    "username": username,
                    "email": email or None,  # "field or None" converts empty strings to None values
                    "airport_iata": airport_iata,
                    "existing_person_id": existing_person_id,
                    # when user wants to drop related event they will send empty string
                    # so we should unconditionally accept new value for event even if
                    # it's an empty string
                    "event": event,
                    "role": role,
                    "errors": [],  # reset here
                    "info": [],
                }
            )

        # save updated data to the session
        request.session["bulk-add-people"] = persons_tasks

        # check if user wants to verify or save, or cancel
        if request.POST.get("verify", None):
            # if there's "verify" in POST, then do only verification
            any_errors = verify_upload_person_task(persons_tasks)
            if any_errors:
                messages.error(request, "Please make sure to fix all errors listed below.")

        # there must be "confirm" and no "cancel" in POST in order to save
        elif request.POST.get("confirm", None) and not request.POST.get("cancel", None):
            try:
                # verification now makes something more than database
                # constraints so we should call it first
                verify_upload_person_task(persons_tasks)
                persons_created, tasks_created = create_uploaded_persons_tasks(persons_tasks, request=request)
            except (IntegrityError, ObjectDoesNotExist, InternalError) as e:
                messages.error(
                    request,
                    f"Error saving data to the database: {e}. Please make sure to fix all errors listed below.",
                )
                any_errors = verify_upload_person_task(persons_tasks)

            else:
                request.session["bulk-add-people"] = None
                messages.success(
                    request,
                    f"Successfully created {len(persons_created)} persons and {len(tasks_created)} tasks.",
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

    roles_list: list[str] = list(Role.objects.all().values_list("name", flat=True))

    context = {
        "title": "Confirm uploaded data",
        "persons_tasks": persons_tasks,
        "any_errors": any_errors,
        "possible_roles": roles_list,
    }
    return render(request, "workshops/person_bulk_add_results.html", context)


@admin_required
@permission_required(["workshops.add_person", "workshops.change_person"], raise_exception=True)
def person_bulk_add_remove_entry(request: AuthenticatedHttpRequest, entry_id: int) -> HttpResponse:
    "Remove specific entry from the session-saved list of people to be added."
    persons_tasks = request.session.get("bulk-add-people")

    if persons_tasks:
        entry_id = int(entry_id)
        try:
            del persons_tasks[entry_id]
            request.session["bulk-add-people"] = persons_tasks

        except IndexError:
            messages.warning(request, f"Could not find specified entry #{entry_id}")

        return redirect(person_bulk_add_confirmation)

    else:
        messages.warning(request, "Could not locate CSV data, please try the upload again.")
        return redirect("person_bulk_add")


@admin_required
@permission_required(["workshops.add_person", "workshops.change_person"], raise_exception=True)
def person_bulk_add_match_person(
    request: AuthenticatedHttpRequest, entry_id: int, person_id: int | None = None
) -> HttpResponse:
    """Save information about matched person in the session-saved data."""
    persons_tasks = request.session.get("bulk-add-people")
    if not persons_tasks:
        messages.warning(request, "Could not locate CSV data, please try the upload again.")
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
                f"Invalid entry ID ({entry_id}) or person ID ({person_id}).",
            )

        except IndexError:
            # catches index out of bound
            messages.warning(request, f"Could not find specified entry #{entry_id}")

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
                f"Invalid entry ID ({entry_id}) or person ID ({person_id}).",
            )

        except IndexError:
            # catches index out of bound
            messages.warning(request, f"Could not find specified entry #{entry_id}")

        return redirect(person_bulk_add_confirmation)


class PersonCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView[PersonCreateForm, Person]):
    permission_required = "workshops.add_person"
    model = Person
    form_class = PersonCreateForm

    def form_valid(self, form: PersonCreateForm) -> HttpResponse:
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

    def get_initial(self) -> dict[str, str]:
        initial = {
            "personal": self.request.GET.get("personal", ""),
            "family": self.request.GET.get("family", ""),
            "email": self.request.GET.get("email", ""),
        }
        return initial


class PersonUpdate(OnlyForAdminsMixin, UserPassesTestMixin, AMYUpdateView[PersonForm, Person]):
    model = Person
    form_class = PersonForm
    pk_url_kwarg = "person_id"
    template_name = "workshops/person_edit_form.html"

    def test_func(self) -> bool:
        if not (self.request.user.has_perm("workshops.change_person") or self.request.user == self.get_object()):
            raise PermissionDenied
        return True

    def get_context_data(self, **kwargs: dict[str, Any]) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        failed_trainings = TrainingProgress.objects.filter(state="f", trainee=self.object).exists()
        kwargs = {
            "initial": {"person": self.object},
            "widgets": {"person": HiddenInput()},
        }

        context.update(
            {
                "awards": self.object.award_set.select_related("event", "badge").order_by("badge__name"),
                "tasks": self.object.task_set.select_related("role", "event").order_by("-event__slug"),
                "consents": self.object.consent_set.select_related("term").order_by("-archived_at"),
                "consents_form": ActiveTermConsentsForm(
                    form_tag=False,
                    prefix="consents",
                    **kwargs,
                ),
                "award_form": AwardForm(
                    form_tag=False,
                    prefix="award",
                    failed_trainings=failed_trainings,
                    **kwargs,
                ),
                "task_form": TaskForm(
                    form_tag=False,
                    prefix="task",
                    failed_trainings=failed_trainings,
                    **kwargs,
                ),
                "community_roles": self.object.communityrole_set.select_related(
                    "config", "award", "inactivation", "membership"
                ),
                "communityrole_form": CommunityRoleForm(
                    form_tag=False,
                    prefix="communityrole",
                    **kwargs,
                ),
            }
        )
        if not self.object.airport_iata:
            messages.warning(self.request, PERSON_HAS_NO_AIRPORT_ALERT.format(person=self.object))
        return context

    def form_valid(self, form: PersonForm) -> HttpResponse:
        self.object = form.save(commit=False)
        # remove existing Qualifications for user
        Qualification.objects.filter(person=self.object).delete()
        # add new Qualifications
        for lesson in form.cleaned_data.pop("lessons"):
            Qualification.objects.create(person=self.object, lesson=lesson)
        result = super().form_valid(form)

        user_tasks = Task.objects.filter(person=self.object, event__isnull=False).select_related("event")
        for task in user_tasks:
            run_ask_for_website_strategy(
                ask_for_website_strategy(task.event),
                self.request,
                task.event,
            )
            run_instructor_training_approaching_strategy(
                instructor_training_approaching_strategy(task.event),
                self.request,
                task.event,
            )
            run_host_instructors_introduction_strategy(
                host_instructors_introduction_strategy(task.event),
                self.request,
                task.event,
            )
            run_recruit_helpers_strategy(
                recruit_helpers_strategy(task.event),
                self.request,
                task.event,
            )
            run_post_workshop_7days_strategy(
                post_workshop_7days_strategy(task.event),
                self.request,
                task.event,
            )
            run_instructor_task_created_for_workshop_strategy(
                instructor_task_created_for_workshop_strategy(task),
                self.request,
                task=task,
                person_id=self.object.pk,
                event_id=task.event.pk,
                task_id=task.pk,
            )

        return result


class PersonDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView[Person, GenericDeleteForm[Person]]):
    model = Person
    permission_required = "workshops.delete_person"
    success_url = reverse_lazy("all_persons")
    pk_url_kwarg = "person_id"


class PersonArchive(PermissionRequiredMixin, LoginRequiredMixin, AMYDeleteView[Person, GenericDeleteForm[Person]]):
    model = Person
    permission_required = "workshops.delete_person"
    pk_url_kwarg = "person_id"
    success_message = "{} was archived successfully."

    def perform_destroy(self, *args: Any, **kwargs: Any) -> None:
        self.object.archive()

    def get_success_url(self) -> str:
        """
        If the user archived their own profile,
        send them to the login page.

        Otherwise send the user back to the page they're currently on.
        """
        if self.request.user.pk == self.object.pk:
            return reverse("login")
        return self.object.get_absolute_url()

    def has_permission(self) -> bool:
        """If the user is archiving their own profile, the user has permission."""
        user_id_being_archived = self.kwargs.get(self.pk_url_kwarg)
        user_archiving_own_profile = self.request.user.pk == user_id_being_archived
        return super().has_permission() or user_archiving_own_profile


class PersonPermissions(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView[PersonPermissionsForm, Person]):
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
def person_password(request: AuthenticatedHttpRequest, person_id: int) -> HttpResponse:
    user = get_object_or_404(Person, pk=person_id)

    # Either the user requests change of their own password, or someone with
    # permission for changing person does.
    if not ((request.user == user) or (request.user.has_perm("workshops.change_person"))):
        raise PermissionDenied

    Form: type[PasswordChangeForm] | type[SetPasswordForm[Person]] = PasswordChangeForm
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

    form.helper = BootstrapHelper(add_cancel_button=False)  # type: ignore
    return render(
        request,
        "generic_form.html",
        {"form": form, "model": Person, "object": user, "title": "Change password"},
    )


@admin_required
@permission_required(["workshops.delete_person", "workshops.change_person"], raise_exception=True)
def persons_merge(request: HttpRequest) -> HttpResponse:
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
        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, settings.ALLOWED_HOSTS):
            return redirect(next_url)
        return render(request, "generic_form.html", context)

    elif obj_a_pk == obj_b_pk:
        context = {
            "title": "Merge Persons",
            "form": PersonsSelectionForm(),
        }
        messages.warning(request, "You cannot merge the same person with themself.")
        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, settings.ALLOWED_HOSTS):
            return redirect(next_url)
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
                "gender",
                "gender_other",
                "airport_iata",
                "country",
                "timezone",
                "github",
                "twitter",
                "bluesky",
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
                "consent_set",
            )

            try:
                _, integrity_errors = merge_objects(obj_a, obj_b, easy, difficult, choices=data, base_a=base_a)

                if integrity_errors:
                    msg = "There were integrity errors when merging related objects:\n\n".join(integrity_errors)
                    messages.warning(request, msg)

            except ProtectedError as e:
                return failed_to_delete(request, object=merging_obj, protected_objects=e.protected_objects)

            else:
                messages.success(
                    request,
                    "Persons were merged successfully. You were redirected to the base person.",
                )
                persons_merged_signal.send(
                    sender=base_obj,
                    request=request,
                    person_a_id=obj_a.id,
                    person_b_id=obj_b.id,
                    selected_person_id=base_obj.id,
                )
                return redirect(base_obj.get_absolute_url())
        else:
            messages.error(request, "Fix errors in the form.")

    context = {
        "title": "Merge two persons",
        "form": form,
        "obj_a": obj_a,
        "obj_b": obj_b,
        "obj_a_consents": {
            consent.term.key: consent
            for consent in Consent.objects.active().select_related("term", "term_option").filter(person=obj_a)
        },
        "obj_b_consents": {
            consent.term.key: consent
            for consent in Consent.objects.active().select_related("term", "term_option").filter(person=obj_b)
        },
    }
    return render(request, "workshops/persons_merge.html", context)


@admin_required
def sync_usersocialauth(request: AuthenticatedHttpRequest, person_id: str | int) -> HttpResponse:
    person_id = int(person_id)
    try:
        person = Person.objects.get(pk=person_id)
    except Person.DoesNotExist:
        messages.error(
            request,
            f"Cannot sync UserSocialAuth table for person #{person_id} -- there is no Person with such id.",
        )
        return redirect(reverse("persons"))
    else:
        try:
            result = person.synchronize_usersocialauth()
            if result:
                messages.success(request, "Social account was successfully synchronized.")
            else:
                messages.error(
                    request,
                    "It was not possible to synchronize this person with their social account.",
                )

        except GithubException:
            messages.error(
                request,
                f"Cannot sync UserSocialAuth table for person #{person_id} due to errors with GitHub API.",
            )

        return redirect(reverse("person_details", args=(person_id,)))


# ------------------------------------------------------------


class AllEvents(OnlyForAdminsMixin, AMYListView[Event]):
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
def event_details(request: AuthenticatedHttpRequest, slug: str) -> HttpResponse:
    """List details of a particular event."""
    event = get_object_or_404(
        Event.objects.attendance().select_related(
            "assigned_to",
            "host",
            "administrator",
            "sponsor",
            "membership",
            "instructorrecruitment",
            "allocated_benefit",
        ),
        slug=slug,
    )

    try:
        recruitment_stats = event.instructorrecruitment.signups.aggregate(
            all_signups=Count("person"),
            pending_signups=Count("person", filter=Q(state="p")),
            discarded_signups=Count("person", filter=Q(state="d")),
            accepted_signups=Count("person", filter=Q(state="a")),
        )
    except Event.instructorrecruitment.RelatedObjectDoesNotExist:
        recruitment_stats = dict(
            all_signups=None,
            pending_signups=None,
            discarded_signups=None,
            accepted_signups=None,
        )

    person_important_badges = Prefetch(
        "person__badges",
        to_attr="important_badges",
        queryset=Badge.objects.filter(name__in=Badge.IMPORTANT_BADGES),
    )

    person_instructor_community_roles = Prefetch(
        "person__communityrole_set",
        to_attr="instructor_community_roles",
        queryset=CommunityRole.objects.filter(config__name="instructor"),
    )

    tasks = (
        Task.objects.filter(event__id=event.id)
        .select_related("event", "person", "role")
        .prefetch_related(
            person_important_badges,
            person_instructor_community_roles,
            Prefetch(
                "person__consent_set",
                to_attr="active_consents",
                queryset=Consent.objects.active().select_related("term", "term_option"),
            ),
        )
        .order_by("role__name")
    )

    admin_lookup_form = AdminLookupForm()
    if event.assigned_to:
        admin_lookup_form = AdminLookupForm(initial={"person": event.assigned_to})

    admin_lookup_form.helper = BootstrapHelper(
        form_action=reverse("event_assign", args=[slug]), add_cancel_button=False
    )
    if hasattr(event, "instructorrecruitment"):
        instructor_recruitment_signups = list(
            InstructorRecruitmentSignup.objects.filter(recruitment=event.instructorrecruitment)
        )
    else:
        instructor_recruitment_signups = []

    context = {
        "title": f"Event {event}",
        "event": event,
        "tasks": tasks,
        "all_emails": tasks.filter(
            person__consent__archived_at__isnull=True,
            person__consent__term_option__option_type=TermOptionChoices.AGREE,
            person__consent__term__slug=TermEnum.MAY_CONTACT,
        )
        .exclude(person__email=None)
        .values_list("person__email", flat=True),
        "today": datetime.date.today(),
        "admin_lookup_form": admin_lookup_form,
        "event_location": {
            "venue": event.venue,
            "humandate": event.human_readable_date(),
            "latitude": event.latitude,
            "longitude": event.longitude,
        },
        "recruitment_stats": recruitment_stats,
        "related_instructor_recruitment_signups": instructor_recruitment_signups,
    }
    return render(request, "workshops/event.html", context)


@admin_required
def validate_event(request: AuthenticatedHttpRequest, slug: str) -> HttpResponse:
    """Check the event's home page *or* the specified URL (for testing)."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist as e:
        raise Http404("Event matching query does not exist.") from e

    page_url = (event.url or "").strip()

    error_messages: list[str] = []
    warning_messages: list[str] = []

    try:
        metadata = fetch_workshop_metadata(page_url)
        # validate metadata
        error_messages, warning_messages = validate_workshop_metadata(metadata)

    except WrongWorkshopURL as e:
        error_messages.append(f"URL error: {e.msg}")

    except requests.exceptions.HTTPError as e:
        error_messages.append(f'Request for "{page_url}" returned status code {e.response.status_code}')

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        error_messages.append("Network connection error.")

    context = {
        "title": f"Validate Event {event}",
        "event": event,
        "page": page_url,
        "error_messages": error_messages,
        "warning_messages": warning_messages,
    }
    return render(request, "workshops/validate_event.html", context)


class EventCreate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYCreateView[EventCreateForm, Event]):
    permission_required = "workshops.add_event"
    model = Event
    form_class = EventCreateForm
    template_name = "workshops/event_create_form.html"
    object: Event
    request: AuthenticatedHttpRequest

    def get_form_kwargs(self) -> dict[str, Any]:
        result = super().get_form_kwargs()
        # Optionally show field `allocated benefit`
        show_allocated_benefit = flag_enabled("SERVICE_OFFERING", request=self.request)
        return result | dict(show_allocated_benefit=show_allocated_benefit)

    def form_valid(self, form: EventCreateForm) -> HttpResponse:
        """Additional functions for validating Event Create form:
        * maybe adding a mail job, if conditions are met
        """
        # save the object
        res = super().form_valid(form)

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(self.object),
            self.request,
            self.object,
        )

        if membership := cast(Membership, form.cleaned_data["membership"]):
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                        membership,
                    ),
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                        membership,
                    ),
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                        membership,
                    ),
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )

        # return remembered results
        return res


class EventUpdate(OnlyForAdminsMixin, PermissionRequiredMixin, AMYUpdateView[EventForm, Event]):
    permission_required = [
        "workshops.change_event",
        "workshops.add_task",
    ]
    queryset = Event.objects.select_related(
        "assigned_to",
        "host",
        "administrator",
        "sponsor",
        "language",
    )
    slug_field = "slug"
    template_name = "workshops/event_edit_form.html"
    object: Event

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        kwargs = {
            "initial": {"event": self.object},
            "widgets": {"event": HiddenInput()},
        }
        show_allocated_benefit = flag_enabled("SERVICE_OFFERING", request=self.request)
        context.update(
            {
                "tasks": self.get_object()
                .task_set.select_related("person", "role")
                .prefetch_related(
                    Prefetch(
                        "person__consent_set",
                        to_attr="active_consents",
                        queryset=Consent.objects.active().select_related("term", "term_option"),
                    ),
                )
                .order_by("role__name"),
                "task_form": TaskForm(
                    form_tag=False, prefix="task", show_allocated_benefit=show_allocated_benefit, **kwargs
                ),
            }
        )
        return context

    def get_form_class(self) -> partial[EventForm]:  # type: ignore[override]
        return partial(
            EventForm,
            show_lessons=True,
            add_comment=True,
            show_allocated_benefit=flag_enabled("SERVICE_OFFERING", request=self.request),
        )

    def form_valid(self, form: EventForm) -> HttpResponse:
        res = super().form_valid(form)

        # TODO: remove this check once SERVICE_OFFERING feature flag is always ON
        if self.object.allocated_benefit and self.object.membership:
            self.object.allocated_benefit = None
            self.object.save()
            messages.warning(
                self.request,
                "This event had both allocated benefit and membership set. Allocated benefit was removed.",
            )

        run_instructor_training_approaching_strategy(
            instructor_training_approaching_strategy(self.object),
            self.request,
            self.object,
        )

        run_host_instructors_introduction_strategy(
            host_instructors_introduction_strategy(self.object),
            self.request,
            self.object,
        )

        run_recruit_helpers_strategy(
            recruit_helpers_strategy(self.object),
            self.request,
            self.object,
        )

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(self.object),
            self.request,
            self.object,
        )

        run_ask_for_website_strategy(
            ask_for_website_strategy(self.object),
            self.request,
            self.object,
        )

        if membership := cast(Membership, form.cleaned_data["membership"]):
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                        membership,
                    ),
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                        membership,
                    ),
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                        membership,
                    ),
                    request=self.request,
                    membership=membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )

        return res


class EventDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView[Event, EventForm]):
    model = Event
    permission_required = "workshops.delete_event"
    success_url = reverse_lazy("all_events")
    object: Event

    def __init__(self) -> None:
        self._membership: Membership | None = None

    def before_delete(self, *args: Any, **kwargs: Any) -> None:
        self._membership = self.object.membership

        run_instructor_training_approaching_strategy(
            instructor_training_approaching_strategy(self.object),
            self.request,
            self.object,
        )

        run_host_instructors_introduction_strategy(
            host_instructors_introduction_strategy(self.object),
            self.request,
            self.object,
        )

        run_recruit_helpers_strategy(
            recruit_helpers_strategy(self.object),
            self.request,
            self.object,
        )

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(self.object),
            self.request,
            self.object,
        )

        run_ask_for_website_strategy(
            ask_for_website_strategy(self.object),
            self.request,
            self.object,
        )

    def after_delete(self, *args: Any, **kwargs: Any) -> None:
        if self._membership:
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                        self._membership,
                    ),
                    request=self.request,
                    membership=self._membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                        self._membership,
                    ),
                    request=self.request,
                    membership=self._membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )
            try:
                run_membership_quarterly_email_strategy(
                    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                    membership_quarterly_email_strategy(
                        MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                        self._membership,
                    ),
                    request=self.request,
                    membership=self._membership,
                )
            except EmailStrategyException as exc:
                messages.error(
                    self.request,
                    f"Error when creating or updating scheduled email. {exc}",
                )


@admin_required
def event_import(request: HttpRequest) -> HttpResponse:
    """Read metadata from remote URL and return them as JSON.

    This is used to read metadata from workshop website and then fill up fields
    on event_create form."""

    url = request.GET.get("url", "").strip()

    try:
        metadata_dict = fetch_workshop_metadata(url)
        # normalize the metadata
        metadata = parse_workshop_metadata(metadata_dict)
        return JsonResponse(metadata)

    except requests.exceptions.HTTPError as e:
        escaped_url = escape(url)
        return HttpResponseBadRequest(f'Request for "{escaped_url}" returned status code {e.response.status_code}.')

    except requests.exceptions.RequestException:
        return HttpResponseBadRequest("Network connection error.")

    except WrongWorkshopURL as e:
        return HttpResponseBadRequest(f"URL error: {e.msg}")

    except KeyError:
        return HttpResponseBadRequest('Missing or wrong "url" parameter.')


class EventAssign(OnlyForAdminsMixin, AssignView[Event]):
    permission_required = "workshops.change_event"
    model = Event
    pk_url_kwarg = "request_id"
    person_url_kwarg = "person_id"


@admin_required
@permission_required(["workshops.delete_event", "workshops.change_event"], raise_exception=True)
def events_merge(request: AuthenticatedHttpRequest) -> HttpResponse:
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
                "sponsor",
                "administrator",
                "public_status",
                "url",
                "language",
                "reg_key",
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
                _, integrity_errors = merge_objects(obj_a, obj_b, easy, difficult, choices=data, base_a=base_a)

                if integrity_errors:
                    msg = "There were integrity errors when merging related objects:\n\n".join(integrity_errors)
                    messages.warning(request, msg)

            except ProtectedError as e:
                return failed_to_delete(request, object=merging_obj, protected_objects=e.protected_objects)

            else:
                messages.success(
                    request,
                    "Events were merged successfully. You were redirected to the base event.",
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
def events_metadata_changed(request: AuthenticatedHttpRequest) -> HttpResponse:
    """List events with metadata changed."""

    assignment_form = AssignmentForm(request.GET)
    assigned_to: Person | None = None
    if assignment_form.is_valid():
        assigned_to = assignment_form.cleaned_data["assigned_to"]

    events = Event.objects.active().filter(metadata_changed=True)

    if assigned_to is not None:
        events = events.filter(assigned_to=assigned_to)

    context = {
        "title": "Events with metadata changed",
        "events": events,
        "assignment_form": assignment_form,
        "assigned_to": assigned_to,
    }
    return render(request, "workshops/events_metadata_changed.html", context)


@admin_required
@permission_required("workshops.change_event", raise_exception=True)
def event_review_metadata_changes(request: AuthenticatedHttpRequest, slug: str) -> HttpResponse:
    """Review changes made to metadata on event's website."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist as e:
        raise Http404("No event found matching the query.") from e

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

    metadata_parsed = parse_workshop_metadata(metadata)

    # save serialized metadata in session so in case of acceptance we don't
    # reload them
    metadata_serialized = metadata_serialize(metadata_parsed)
    request.session["metadata_from_event_website"] = metadata_serialized

    context = {
        "title": f"Review changes for {str(event)}",
        "metadata": metadata_parsed,
        "event": event,
    }
    return render(request, "workshops/event_review_metadata_changes.html", context)


@admin_required
@permission_required("workshops.change_event", raise_exception=True)
def event_accept_metadata_changes(request: AuthenticatedHttpRequest, slug: str) -> HttpResponse:
    """Review changes made to metadata on event's website."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist as e:
        raise Http404("No event found matching the query.") from e

    # load serialized metadata from session
    metadata_serialized = request.session.get("metadata_from_event_website")
    if not metadata_serialized:
        raise Http404("Nothing to update.")

    metadata = metadata_deserialize(metadata_serialized)

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
    comment_txt = f"INSTRUCTORS: {instructors}\n\nHELPERS: {helpers}"
    add_comment(event, comment_txt)

    # save serialized metadata
    event.repository_metadata = metadata_serialized

    # dismiss notification
    event.metadata_all_changes = ""
    event.metadata_changed = False
    event.save()

    # remove metadata from session
    del request.session["metadata_from_event_website"]

    messages.success(request, f"Successfully updated {event.slug}.")

    return redirect(reverse("event_details", args=[event.slug]))


@admin_required
@permission_required("workshops.change_event", raise_exception=True)
def event_dismiss_metadata_changes(request: AuthenticatedHttpRequest, slug: str) -> HttpResponse:
    """Review changes made to metadata on event's website."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist as e:
        raise Http404("No event found matching the query.") from e

    # dismiss notification
    event.metadata_all_changes = ""
    event.metadata_changed = False
    event.save()

    # remove metadata from session
    if "metadata_from_event_website" in request.session:
        del request.session["metadata_from_event_website"]

    messages.success(request, f"Changes to {event.slug} were dismissed.")

    return redirect(reverse("event_details", args=[event.slug]))


# ------------------------------------------------------------


class AllTasks(OnlyForAdminsMixin, AMYListView[Task]):
    context_object_name = "all_tasks"
    template_name = "workshops/all_tasks.html"
    filter_class = TaskFilter
    queryset = Task.objects.select_related("event", "person", "role").prefetch_related(
        Prefetch(
            "person__consent_set",
            to_attr="active_consents",
            queryset=Consent.objects.active().select_related("term", "term_option"),
        ),
    )
    title = "All Tasks"


class TaskDetails(OnlyForAdminsMixin, AMYDetailView[Task]):
    queryset = Task.objects.all()
    context_object_name = "task"
    pk_url_kwarg = "task_id"
    template_name = "workshops/task.html"

    def get_context_data(self, **kwargs: dict[str, Any]) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f"Task {self.object}"
        return context


class TaskCreate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    RedirectSupportMixin,
    AMYCreateView[TaskForm, Task],
):
    permission_required = "workshops.add_task"
    model = Task
    form_class = TaskForm

    def get_form_kwargs(self) -> dict[str, str]:
        kwargs = super().get_form_kwargs()
        kwargs.update({"prefix": "task"})
        # Optionally show field `allocated benefit`
        show_allocated_benefit = flag_enabled("SERVICE_OFFERING", request=self.request)
        return kwargs | dict(show_allocated_benefit=show_allocated_benefit)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Save request in `self.request`."""
        self.request = request
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: TaskForm) -> HttpResponse:
        """Additional functions for validating Task Create form:

        * checking membership seats, availability
        * maybe adding a mail job, if conditions are met
        """

        seat_membership = form.cleaned_data["seat_membership"]
        event = form.cleaned_data["event"]
        # This field is no longer available in the form.
        # seat_public = form.cleaned_data["seat_public"]

        # check associated membership remaining seats and validity
        if hasattr(self, "request") and seat_membership is not None:
            # Assume seat_public is True if not provided (for backward compatibility)
            seat_public = True

            remaining = (
                seat_membership.public_instructor_training_seats_remaining
                if seat_public
                else seat_membership.inhouse_instructor_training_seats_remaining
            )
            # check number of available seats
            if remaining == 1:
                messages.warning(
                    self.request,
                    # after the form is saved there will be 0 remaining seats
                    f'Membership "{seat_membership}" has no '
                    f"{'public' if seat_public else 'in-house'} instructor training "
                    "seats remaining.",
                )
            if remaining <= 0:
                messages.warning(
                    self.request,
                    f'Membership "{seat_membership}" is using more '
                    f"{'public' if seat_public else 'in-house'} training seats than "
                    "it's been allowed.",
                )

            today = datetime.date.today()
            # check if membership is active
            if not (seat_membership.agreement_start <= today <= seat_membership.agreement_end):
                messages.warning(
                    self.request,
                    f'Membership "{seat_membership}" is not active.',
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
                    f'Training "{event}" has start or end date outside membership "{seat_membership}" agreement dates.',
                )

        # save the object
        res = super().form_valid(form)
        self.object: Task  # created and saved to DB by super().form_valid()

        run_instructor_training_approaching_strategy(
            instructor_training_approaching_strategy(event),
            self.request,
            event,
        )

        run_host_instructors_introduction_strategy(
            host_instructors_introduction_strategy(event),
            self.request,
            event,
        )

        run_recruit_helpers_strategy(
            recruit_helpers_strategy(event),
            self.request,
            event,
        )

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(event),
            self.request,
            event,
        )

        run_ask_for_website_strategy(
            ask_for_website_strategy(event),
            self.request,
            event,
        )

        run_instructor_task_created_for_workshop_strategy(
            instructor_task_created_for_workshop_strategy(self.object),
            self.request,
            task=self.object,
            person_id=self.object.person.pk,
            event_id=event.pk,
            task_id=self.object.pk,
        )

        if seat_membership:
            update_context_json_and_to_header_json(
                signal_name=MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
                request=self.request,
                membership=seat_membership,
            )
            update_context_json_and_to_header_json(
                signal_name=MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
                request=self.request,
                membership=seat_membership,
            )
            update_context_json_and_to_header_json(
                signal_name=MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
                request=self.request,
                membership=seat_membership,
            )

        # return remembered results
        return res


class TaskUpdate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    AMYUpdateView[TaskForm, Task],
):
    permission_required = "workshops.change_task"
    model = Task
    queryset = Task.objects.select_related("event", "role", "person", "seat_membership", "allocated_benefit")
    form_class = TaskForm
    pk_url_kwarg = "task_id"
    object: Task

    def get_form_kwargs(self) -> dict[str, Any]:
        result = super().get_form_kwargs()
        # Optionally show field `allocated benefit`
        show_allocated_benefit = flag_enabled("SERVICE_OFFERING", request=self.request)
        return result | dict(show_allocated_benefit=show_allocated_benefit)

    def form_valid(self, form: TaskForm) -> HttpResponse:
        res = super().form_valid(form)

        seat_membership = form.cleaned_data["seat_membership"]

        # TODO: remove this check once SERVICE_OFFERING feature flag is always ON
        if self.object.allocated_benefit and seat_membership:
            self.object.allocated_benefit = None
            self.object.save()
            messages.warning(
                self.request,
                "This task had both allocated benefit and membership set. Allocated benefit was removed.",
            )

        # This field is no longer available in the form.
        # seat_public = form.cleaned_data["seat_public"]

        # check associated membership remaining seats and validity
        if hasattr(self, "request") and seat_membership is not None:
            # Assume seat_public is True if not provided (for backward compatibility)
            seat_public = True

            remaining = (
                seat_membership.public_instructor_training_seats_remaining
                if seat_public
                else seat_membership.inhouse_instructor_training_seats_remaining
            )
            # check number of available seats
            if remaining == 0:
                messages.warning(
                    self.request,
                    f'Membership "{seat_membership}" has no '
                    f"{'public' if seat_public else 'in-house'} instructor training "
                    "seats remaining.",
                )
            if remaining < 0:
                messages.warning(
                    self.request,
                    f'Membership "{seat_membership}" is using more '
                    f"{'public' if seat_public else 'in-house'} training seats than "
                    "it's been allowed.",
                )

        run_instructor_training_approaching_strategy(
            instructor_training_approaching_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_host_instructors_introduction_strategy(
            host_instructors_introduction_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_recruit_helpers_strategy(
            recruit_helpers_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_ask_for_website_strategy(
            ask_for_website_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_instructor_task_created_for_workshop_strategy(
            instructor_task_created_for_workshop_strategy(self.object),
            self.request,
            task=self.object,
            person_id=self.object.person.pk,
            event_id=self.object.event.pk,
            task_id=self.object.pk,
        )

        return res


class TaskDelete(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    RedirectSupportMixin,
    AMYDeleteView[Task, GenericDeleteForm[Task]],
):
    model = Task
    permission_required = "workshops.delete_task"
    success_url = reverse_lazy("all_tasks")
    pk_url_kwarg = "task_id"
    object: Task

    def before_delete(self, *args: Any, **kwargs: Any) -> None:
        self.old: Task = self.get_object()
        self.old_pk = self.old.pk
        self.event = self.old.event

    def after_delete(self, *args: Any, **kwargs: Any) -> None:
        run_instructor_training_approaching_strategy(
            instructor_training_approaching_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_host_instructors_introduction_strategy(
            host_instructors_introduction_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_recruit_helpers_strategy(
            recruit_helpers_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_post_workshop_7days_strategy(
            post_workshop_7days_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_ask_for_website_strategy(
            ask_for_website_strategy(self.object.event),
            self.request,
            self.object.event,
        )

        run_instructor_task_created_for_workshop_strategy(
            instructor_task_created_for_workshop_strategy(self.object, self.old_pk),
            self.request,
            task=self.old,
            person_id=self.object.person.pk,
            event_id=self.event.pk,
            task_id=self.old_pk,
        )


# ------------------------------------------------------------


class MockAwardCreate(
    OnlyForAdminsMixin,
    PermissionRequiredMixin,
    PrepopulationSupportMixin[AwardForm],
    AMYCreateView[AwardForm, Award],
):
    permission_required = "workshops.add_award"
    model = Award
    form_class = AwardForm
    populate_fields = ["badge", "person"]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs.update({"prefix": "award"})
        return kwargs

    def get_initial(self, **kwargs: Any) -> dict[str, Any]:
        initial = super().get_initial(**kwargs)

        # Determine initial event in AwardForm
        if "find-training" in self.request.GET:
            initial["badge"] = Badge.objects.get(name="instructor")
            try:
                progress = TrainingProgress.objects.get(
                    trainee__id=self.request.GET["person"],
                    requirement=TrainingRequirement.objects.get(name="Training"),
                    state="p",
                )
                initial["event"] = progress.event
            except (
                TrainingProgress.DoesNotExist,
                TrainingProgress.MultipleObjectsReturned,
            ):
                pass

        return initial

    def get_success_url(self) -> str:
        return reverse("badge_details", args=[self.object.badge.name])

    def form_valid(self, form: AwardForm) -> HttpResponse:
        result = super().form_valid(form)
        self.object: Award  # created and saved to DB by super().form_valid()

        # Check for CommunityRoles that should automatically be created.
        badge = self.object.badge
        person = self.object.person
        event = self.object.event
        community_role_configs = CommunityRoleConfig.objects.filter(
            award_badge_limit=badge,
            autoassign_when_award_created=True,
        )
        if community_role_configs:
            start_date = datetime.date.today()
            roles = [
                CommunityRole(
                    config=config,
                    person=person,
                    award=self.object,
                    start=start_date,
                    end=None,
                    inactivation=None,
                    membership=None,
                    url="",
                )
                for config in community_role_configs
                if not CommunityRoleForm.find_concurrent_roles(config, person, start_date)
            ]
            logger.debug(f"Automatically creating community roles set up for badge {badge}")
            roles_result = CommunityRole.objects.bulk_create(roles)
            logger.debug(f"Created {len(roles_result)} Community Roles for badge {badge} and person {person}")

        run_instructor_badge_awarded_strategy(
            instructor_badge_awarded_strategy(self.object, self.object.person),
            self.request,
            self.object.person,
            award_id=self.object.pk,
            person_id=person.pk,
        )

        try:
            run_instructor_training_completed_not_badged_strategy(
                instructor_training_completed_not_badged_strategy(person),
                request=self.request,
                person=person,
                training_completed_date=event.end if event else None,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when running instructor training completed strategy. {exc}",
            )

        return result


class AwardCreate(RedirectSupportMixin, MockAwardCreate):
    pass


class MockAwardDelete(OnlyForAdminsMixin, PermissionRequiredMixin, AMYDeleteView[Award, GenericDeleteForm[Award]]):
    model = Award
    permission_required = "workshops.delete_award"
    object: Award

    def back_address(self) -> str | None:
        fallback_url = reverse("person_edit", args=[self.get_object().person.id])
        referrer = self.request.headers.get("Referer", fallback_url)
        return safe_next_or_default_url(referrer, fallback_url)

    def before_delete(self, *args: Any, **kwargs: Any) -> None:
        """Save for use in `after_delete` method."""
        self._award = self.object
        self._award_pk = self.object.pk
        self._person = self.object.person

    def after_delete(self, *args: Any, **kwargs: Any) -> None:
        award = self._award
        award_pk = self._award_pk
        person = self._person
        try:
            run_instructor_badge_awarded_strategy(
                instructor_badge_awarded_strategy(award, person, award_pk),
                request=self.request,
                person=person,
                award_id=award_pk,
                person_id=person.pk,
            )
        except EmailStrategyException as exc:
            messages.error(
                self.request,
                f"Error when running instructor badge awarded strategy. {exc}",
            )

    def get_success_url(self) -> str:
        return reverse("badge_details", args=[self.get_object().badge.name])


class AwardDelete(RedirectSupportMixin, MockAwardDelete):
    # Modify the MRO to look like:
    # AwardDelete < RedirectSupportMixin < MockAwardDelete
    #
    # This ensures that `super()` when called from `get_success_url` method of
    # RedirectSupportMixin returns MockAwardDelete
    pass


# ------------------------------------------------------------


class AllBadges(OnlyForAdminsMixin, AMYListView[Badge]):
    context_object_name = "all_badges"
    queryset = Badge.objects.order_by("name").annotate(num_awarded=Count("award"))
    template_name = "workshops/all_badges.html"
    title = "All Badges"


class BadgeDetails(OnlyForAdminsMixin, AMYDetailView[Badge]):
    queryset = Badge.objects.all()
    context_object_name = "badge"
    template_name = "workshops/badge.html"
    slug_field = "name"
    slug_url_kwarg = "badge_name"

    def get_context_data(self, **kwargs: dict[str, Any]) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["title"] = f"Badge {self.object}"
        filter = BadgeAwardsFilter(
            self.request.GET,
            queryset=self.object.award_set.select_related("event", "person", "badge").prefetch_related(
                Prefetch(
                    "person__consent_set",
                    to_attr="active_consents",
                    queryset=Consent.objects.active().select_related("term", "term_option"),
                ),
            ),
        )
        context["filter"] = filter

        awards = get_pagination_items(self.request, filter.qs)
        context["awards"] = awards

        return context


# ------------------------------------------------------------


class PersonWorkshopStaffAnnotation(TypedDict):
    # From PersonRoleCount typed dict defined in `workshops/models.py`
    num_instructor: int
    num_trainer: int
    num_helper: int
    num_learner: int
    num_supporting: int
    num_organizer: int

    is_trainee: int
    is_trainer: int
    is_instructor: int


def _workshop_staff_query(
    lat: float | None = None, lng: float | None = None
) -> QuerySet[Annotated[Person, Annotations[PersonWorkshopStaffAnnotation]]]:
    """This query is used in two views: workshop staff searching and its CSV
    results. Thanks to factoring-out this function, we're now quite certain
    that the results in both of the views are the same."""
    TTT = Tag.objects.get(name="TTT")
    stalled = Tag.objects.get(name="stalled")
    learner = Role.objects.get(name="learner")
    instructor_badges = Badge.objects.filter(name__in=Badge.INSTRUCTOR_BADGES)

    trainee_tasks = (
        Task.objects.filter(event__tags=TTT, role=learner)
        .exclude(event__tags=stalled)
        .exclude(person__badges__in=instructor_badges)
    )

    active_instructor_community_roles = CommunityRole.objects.active().filter(config__name="instructor")

    # we need to count number of specific roles users had
    # and if they are instructors
    people = (
        Person.objects.annotate_with_role_count()
        .annotate(
            is_trainee=Count("task", filter=Q(task__in=trainee_tasks)),
            is_trainer=Count("badges", filter=Q(badges__name="trainer")),
            is_instructor=Count(
                "communityrole",
                filter=Q(communityrole__in=active_instructor_community_roles),
            ),
        )
        .exclude(airport_iata="")
        .prefetch_related(
            "lessons",
            Prefetch(
                "communityrole_set",
                to_attr="instructor_community_roles",
                queryset=CommunityRole.objects.filter(config__name="instructor"),
            ),
            Prefetch(
                "consent_set",
                to_attr="active_consents",
                queryset=Consent.objects.active().select_related("term", "term_option"),
            ),
        )
        .order_by("family", "personal")
    )

    if lat and lng:
        # using Euclidean distance just because it's faster and easier
        complex_F = (F("airport_lat") - lat) ** 2 + (F("airport_lon") - lng) ** 2
        people = people.annotate(distance=ExpressionWrapper(complex_F, output_field=FloatField())).order_by(
            "distance", "family"
        )

    return people


@admin_required
def workshop_staff(request: AuthenticatedHttpRequest) -> HttpResponse:
    """Search for workshop staff."""

    # read data from form, if it was submitted correctly
    lat, lng = None, None
    lessons = list()
    form = WorkshopStaffForm(request.GET)
    if form.is_valid():
        # to highlight (in template) what lessons people know
        lessons = form.cleaned_data["lessons"]

        if (airport_iata := form.cleaned_data["airport_iata"]) and airport_iata in IATA_AIRPORTS:
            airport = IATA_AIRPORTS[airport_iata]
            lat = airport["lat"]
            lng = airport["lon"]

        elif form.cleaned_data["latitude"] and form.cleaned_data["longitude"]:
            lat = form.cleaned_data["latitude"]
            lng = form.cleaned_data["longitude"]

    # prepare the query
    people_query = _workshop_staff_query(lat, lng)

    # filter the query
    f = WorkshopStaffFilter(request.GET, queryset=people_query)
    people = get_pagination_items(request, f.qs)

    context = {
        "title": "Find Workshop Staff",
        "filter_form": form,
        "persons": people,
        "lessons": lessons,
    }
    return render(request, "workshops/workshop_staff.html", context)


@admin_required
def workshop_staff_csv(request: AuthenticatedHttpRequest) -> HttpResponse:
    """Generate CSV of workshop staff search results."""

    # read data from form, if it was submitted correctly
    lat, lng = None, None
    form = WorkshopStaffForm(request.GET)
    if form.is_valid():
        if (airport_iata := form.cleaned_data["airport_iata"]) and airport_iata in IATA_AIRPORTS:
            airport = IATA_AIRPORTS[airport_iata]
            lat = airport["lat"]
            lng = airport["lon"]

        elif form.cleaned_data["latitude"] and form.cleaned_data["longitude"]:
            lat = form.cleaned_data["latitude"]
            lng = form.cleaned_data["longitude"]

    # prepare the query
    people_query = _workshop_staff_query(lat, lng)

    # filter the query
    f = WorkshopStaffFilter(request.GET, queryset=people_query)
    people = f.qs

    # first row of the CSV output
    header_row = (
        "Name",
        "Email",
        "Is instructor",
        "Is trainer",
        "Taught times",
        "Is trainee",
        "Airport",
        "Country",
        "Lessons",
        "Affiliation",
    )

    # CSV http header
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="WorkshopStaff.csv"'
    # CSV output
    writer = csv.writer(response)
    writer.writerow(header_row)
    for person in people:
        writer.writerow(
            [
                person.full_name,
                person.email,
                "yes" if person.is_instructor else "no",
                "yes" if person.is_trainer else "no",
                person.num_instructor,
                "yes" if person.is_trainee else "no",
                person.airport_iata,
                person.country.name if person.country else "",
                " ".join([lesson.name for lesson in person.lessons.all()]),
                person.affiliation or "",
            ]
        )
    return response


# ------------------------------------------------------------


@admin_required
def object_changes(request: AuthenticatedHttpRequest, version_id: int) -> HttpResponse:
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
        previous_version = Version.objects.get_for_object(obj).filter(pk__lt=current_version.pk)[0]
    except IndexError:
        # first revision for an object
        previous_version = current_version

    # set default versions displayed in the template
    version2 = current_version
    version1 = previous_version

    # set default ordering: latest first
    history_latest_first = True

    def _order(queryset: QuerySet[Version]) -> QuerySet[Version]:
        """Applies the correct ordering to the given version queryset."""
        return queryset.order_by("-pk" if history_latest_first else "pk")

    # get action list
    action_list: list[dict[str, Any]] = [
        {"version": version, "revision": version.revision}
        for version in _order(Version.objects.get_for_object(obj).select_related("revision__user"))
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
        "verbose_name": obj._meta.verbose_name,  # type: ignore[union-attr]
        "object": obj,
        "version1": version1,
        "version2": version2,
        "revision": version2.revision,
        "fields": [f for f in obj._meta.get_fields() if f.concrete],  # type: ignore[union-attr]
        "action": "",
        "compare_view": True,
        "action_list": action_list,
        "comparable": len(action_list) >= 2,
    }
    return render(request, "workshops/object_diff.html", context)
