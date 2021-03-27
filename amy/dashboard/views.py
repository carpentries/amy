import re
from typing import Optional

from django.contrib import messages
from django.db.models import (
    Case,
    When,
    Value,
    IntegerField,
    Count,
    Prefetch,
    Q,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.html import format_html
from django.urls import reverse
from django.views.decorators.http import require_GET
from django_comments.models import Comment

from fiscal.models import MembershipTask
from workshops.models import (
    Airport,
    Badge,
    Event,
    Qualification,
    Person,
    Task,
    Organization,
    Membership,
    Tag,
    TrainingRequest,
    TrainingProgress,
)
from workshops.util import (
    login_required,
    admin_required,
)
from dashboard.forms import (
    AssignmentForm,
    AutoUpdateProfileForm,
    SendHomeworkForm,
    SearchForm,
)


@login_required
def dispatch(request):
    """If user is admin, then show them admin dashboard; otherwise redirect
    them to trainee dashboard."""
    if request.user.is_admin:
        return redirect(reverse("admin-dashboard"))
    else:
        return redirect(reverse("trainee-dashboard"))


@admin_required
def admin_dashboard(request):
    """Home page for admins."""
    data = request.GET.copy()
    if "assigned_to" not in data:
        data["assigned_to"] = request.user.id
    assignment_form = AssignmentForm(data)
    assigned_to: Optional[Person] = None
    if assignment_form.is_valid():
        assigned_to = assignment_form.cleaned_data["assigned_to"]

    current_events = Event.objects.current_events().prefetch_related("tags")

    # This annotation may produce wrong number of instructors when
    # `unpublished_events` filters out events that contain a specific tag.
    # The bug was fixed in #1130.
    unpublished_events = (
        Event.objects.active()
        .unpublished_events()
        .select_related("host")
        .annotate(
            num_instructors=Count(
                Case(
                    When(task__role__name="instructor", then=Value(1)),
                    output_field=IntegerField(),
                )
            ),
        )
        .order_by("-start")
    )

    # assigned events that have unaccepted changes
    updated_metadata = Event.objects.active().filter(metadata_changed=True)

    current_events = current_events.filter(assigned_to=assigned_to)
    unpublished_events = unpublished_events.filter(assigned_to=assigned_to)
    updated_metadata = updated_metadata.filter(assigned_to=assigned_to)

    context = {
        "title": None,
        "assignment_form": assignment_form,
        "assigned_to": assigned_to,
        "current_events": current_events,
        "unpublished_events": unpublished_events,
        "updated_metadata": updated_metadata.count(),
        "main_tags": Tag.objects.main_tags(),
    }
    return render(request, "dashboard/admin_dashboard.html", context)


# ------------------------------------------------------------
# Views for trainees


@login_required
def trainee_dashboard(request):
    qs = Person.objects.select_related("airport").prefetch_related(
        "badges",
        "lessons",
        "domains",
        "languages",
        Prefetch(
            "task_set",
            queryset=Task.objects.select_related(),
        ),
        Prefetch(
            "membershiptask_set",
            queryset=MembershipTask.objects.select_related(),
        ),
    )
    user = get_object_or_404(qs, id=request.user.id)

    context = {
        "title": "Your profile",
        "user": user,
    }
    return render(request, "dashboard/trainee_dashboard.html", context)


@login_required
def autoupdate_profile(request):
    person = request.user
    form = AutoUpdateProfileForm(instance=person)

    if request.method == "POST":
        form = AutoUpdateProfileForm(request.POST, instance=person)

        if form.is_valid() and form.instance == person:
            # save lessons
            person.lessons.clear()
            for lesson in form.cleaned_data["lessons"]:
                q = Qualification(lesson=lesson, person=person)
                q.save()

            # don't save related lessons
            del form.cleaned_data["lessons"]

            person = form.save()

            messages.success(request, "Your profile was updated.")

            return redirect(reverse("trainee-dashboard"))
        else:
            messages.error(request, "Fix errors below.")

    context = {
        "title": "Update Your Profile",
        "form": form,
    }
    return render(request, "dashboard/autoupdate_profile.html", context)


@login_required
def training_progress(request):
    homework_form = SendHomeworkForm()

    # Add information about instructor training progress to request.user.
    request.user = (
        Person.objects.annotate_with_instructor_eligibility()
        .prefetch_related(
            Prefetch(
                "badges",
                to_attr="instructor_badges",
                queryset=Badge.objects.instructor_badges(),
            ),
        )
        .get(pk=request.user.pk)
    )

    progresses = request.user.trainingprogress_set.filter(discarded=False)
    last_swc_homework = (
        progresses.filter(requirement__name="SWC Homework")
        .order_by("-created_at")
        .first()
    )
    request.user.swc_homework_in_evaluation = (
        last_swc_homework is not None and last_swc_homework.state == "n"
    )
    last_dc_homework = (
        progresses.filter(requirement__name="DC Homework")
        .order_by("-created_at")
        .first()
    )
    request.user.dc_homework_in_evaluation = (
        last_dc_homework is not None and last_dc_homework.state == "n"
    )
    last_lc_homework = (
        progresses.filter(requirement__name="LC Homework")
        .order_by("-created_at")
        .first()
    )
    request.user.lc_homework_in_evaluation = (
        last_lc_homework is not None and last_lc_homework.state == "n"
    )

    if request.method == "POST":
        homework_form = SendHomeworkForm(data=request.POST)
        if homework_form.is_valid():
            # read homework type from POST
            hw_type = homework_form.cleaned_data["requirement"]

            # create "empty" progress object and fill out
            progress = TrainingProgress(
                trainee=request.user,
                state="n",  # not evaluated yet
                requirement=hw_type,
            )

            # create virtual form to validate and save
            form = SendHomeworkForm(data=request.POST, instance=progress)
            if form.is_valid():
                form.save()
                messages.success(
                    request, "Your homework submission will be " "evaluated soon."
                )
                return redirect(reverse("training-progress"))

    context = {
        "title": "Your training progress",
        "homework_form": homework_form,
    }
    return render(request, "dashboard/training_progress.html", context)


# ------------------------------------------------------------


@require_GET
@admin_required
def search(request):
    """Search the database by term."""

    term = ""
    organizations = None
    memberships = None
    events = None
    persons = None
    airports = None
    training_requests = None
    comments = None
    single_results = []

    if request.method == "GET" and "term" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            term = form.cleaned_data.get("term", "")
            tokens = re.split(r"\s+", term)

            organizations = Organization.objects.filter(
                Q(domain__icontains=term) | Q(fullname__icontains=term)
            ).order_by("fullname")
            if len(organizations) == 1:
                single_results.append(organizations[0])

            memberships = Membership.objects.filter(
                Q(name__icontains=term) | Q(registration_code__icontains=term)
            ).order_by("-agreement_start")
            if len(memberships) == 1:
                single_results.append(memberships[0])

            events = Event.objects.filter(
                Q(slug__icontains=term)
                | Q(host__domain__icontains=term)
                | Q(host__fullname__icontains=term)
                | Q(url__icontains=term)
                | Q(contact__icontains=term)
                | Q(venue__icontains=term)
                | Q(address__icontains=term)
            ).order_by("-slug")
            if len(events) == 1:
                single_results.append(events[0])

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

            if len(persons) == 1:
                single_results.append(persons[0])

            airports = Airport.objects.filter(
                Q(iata__icontains=term) | Q(fullname__icontains=term)
            ).order_by("iata")
            if len(airports) == 1:
                single_results.append(airports[0])

            training_requests = TrainingRequest.objects.filter(
                Q(group_name__icontains=term)
                | Q(family__icontains=term)
                | Q(email__icontains=term)
                | Q(github__icontains=term)
                | Q(affiliation__icontains=term)
                | Q(location__icontains=term)
                | Q(user_notes__icontains=term)
            )
            if len(training_requests) == 1:
                single_results.append(training_requests[0])

            comments = Comment.objects.filter(
                Q(comment__icontains=term)
                | Q(user_name__icontains=term)
                | Q(user_email__icontains=term)
                | Q(user__personal__icontains=term)
                | Q(user__family__icontains=term)
                | Q(user__email__icontains=term)
                | Q(user__github__icontains=term)
            ).prefetch_related("content_object")
            if len(comments) == 1:
                single_results.append(comments[0])

            # only 1 record found? Let's move to it immediately
            if len(single_results) == 1 and not form.cleaned_data["no_redirect"]:
                result = single_results[0]
                msg = format_html(
                    "You were moved to this page, because your search <i>{}</i> "
                    "yields only this result.",
                    term,
                )
                if isinstance(result, Comment):
                    messages.success(request, msg)
                    return redirect(
                        result.content_object.get_absolute_url()
                        + "#c{}".format(result.id)
                    )
                elif hasattr(result, "get_absolute_url"):
                    messages.success(request, msg)
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
        "organisations": organizations,
        "memberships": memberships,
        "events": events,
        "persons": persons,
        "airports": airports,
        "comments": comments,
        "training_requests": training_requests,
    }
    return render(request, "dashboard/search.html", context)
