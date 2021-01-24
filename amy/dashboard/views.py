import re

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
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET
from django_comments.models import Comment

from workshops.forms import SearchForm
from workshops.models import (
    Airport,
    Badge,
    Event,
    Qualification,
    Person,
    Organization,
    Tag,
    TrainingRequest,
    TrainingProgress,
)
from workshops.util import (
    login_required,
    admin_required,
    is_admin,
    assignment_selection,
)
from dashboard.forms import (
    AutoUpdateProfileForm,
    SendHomeworkForm,
)


@login_required
def dispatch(request):
    """If user is admin, then show them admin dashboard; otherwise redirect
    them to trainee dashboard."""
    if is_admin(request.user):
        return redirect(reverse('admin-dashboard'))
    else:
        return redirect(reverse('trainee-dashboard'))


@admin_required
def admin_dashboard(request):
    """Home page for admins."""

    current_events = (
        Event.objects.upcoming_events() | Event.objects.ongoing_events()
    ).active().prefetch_related('tags')

    # This annotation may produce wrong number of instructors when
    # `unpublished_events` filters out events that contain a specific tag.
    # The bug was fixed in #1130.
    unpublished_events = Event.objects \
        .active().unpublished_events().select_related('host').annotate(
            num_instructors=Count(
                Case(
                    When(task__role__name='instructor', then=Value(1)),
                    output_field=IntegerField()
                )
            ),
        ).order_by('-start')

    assigned_to, is_admin = assignment_selection(request)

    if assigned_to == 'me':
        current_events = current_events.filter(assigned_to=request.user)
        unpublished_events = unpublished_events.filter(
            assigned_to=request.user)

    elif assigned_to == 'noone':
        current_events = current_events.filter(assigned_to__isnull=True)
        unpublished_events = unpublished_events.filter(
            assigned_to__isnull=True)

    elif assigned_to == 'all':
        # no filtering
        pass

    else:
        # no filtering
        pass

    # assigned events that have unaccepted changes
    updated_metadata = Event.objects.active() \
                                    .filter(assigned_to=request.user) \
                                    .filter(metadata_changed=True) \
                                    .count()

    context = {
        'title': None,
        'is_admin': is_admin,
        'assigned_to': assigned_to,
        'current_events': current_events,
        'unpublished_events': unpublished_events,
        'updated_metadata': updated_metadata,
        'main_tags': Tag.objects.main_tags(),
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


# ------------------------------------------------------------
# Views for trainees


@login_required
def trainee_dashboard(request):
    # Workshops person taught at
    workshops = request.user.task_set.select_related('role', 'event')

    context = {
        'title': 'Your profile',
        'workshops': workshops,
    }
    return render(request, 'dashboard/trainee_dashboard.html', context)


@login_required
def autoupdate_profile(request):
    person = request.user
    form = AutoUpdateProfileForm(instance=person)

    if request.method == 'POST':
        form = AutoUpdateProfileForm(request.POST, instance=person)

        if form.is_valid() and form.instance == person:
            # save lessons
            person.lessons.clear()
            for lesson in form.cleaned_data['lessons']:
                q = Qualification(lesson=lesson, person=person)
                q.save()

            # don't save related lessons
            del form.cleaned_data['lessons']

            person = form.save()

            messages.success(request, 'Your profile was updated.')

            return redirect(reverse('trainee-dashboard'))
        else:
            messages.error(request, 'Fix errors below.')

    context = {
        'title': 'Update Your Profile',
        'form': form,
    }
    return render(request, 'dashboard/autoupdate_profile.html', context)


@login_required
def training_progress(request):
    homework_form = SendHomeworkForm()

    # Add information about instructor training progress to request.user.
    request.user = Person.objects \
        .annotate_with_instructor_eligibility() \
        .prefetch_related(Prefetch(
            'badges',
            to_attr='instructor_badges',
            queryset=Badge.objects.instructor_badges()),
        ).get(pk=request.user.pk)

    progresses = request.user.trainingprogress_set.filter(discarded=False)
    last_swc_homework = progresses.filter(
        requirement__name='SWC Homework').order_by('-created_at').first()
    request.user.swc_homework_in_evaluation = (
        last_swc_homework is not None and last_swc_homework.state == 'n')
    last_dc_homework = progresses.filter(
        requirement__name='DC Homework').order_by('-created_at').first()
    request.user.dc_homework_in_evaluation = (
        last_dc_homework is not None and last_dc_homework.state == 'n')
    last_lc_homework = progresses.filter(
        requirement__name='LC Homework').order_by('-created_at').first()
    request.user.lc_homework_in_evaluation = (
        last_lc_homework is not None and last_lc_homework.state == 'n')

    if request.method == 'POST':
        homework_form = SendHomeworkForm(data=request.POST)
        if homework_form.is_valid():
            # read homework type from POST
            hw_type = homework_form.cleaned_data['requirement']

            # create "empty" progress object and fill out
            progress = TrainingProgress(
                trainee=request.user,
                state='n',  # not evaluated yet
                requirement=hw_type,
            )

            # create virtual form to validate and save
            form = SendHomeworkForm(data=request.POST, instance=progress)
            if form.is_valid():
                form.save()
                messages.success(request, "Your homework submission will be "
                                          "evaluated soon.")
                return redirect(reverse('training-progress'))

    context = {
        'title': 'Your training progress',
        'homework_form': homework_form,
    }
    return render(request, 'dashboard/training_progress.html', context)


# ------------------------------------------------------------


@require_GET
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
