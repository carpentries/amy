from django.contrib import messages
from django.db.models import (
    Case,
    When,
    Value,
    IntegerField,
    Count,
)
from django.shortcuts import render, redirect
from django.urls import reverse

from workshops.models import (
    Event,
    Tag,
    Qualification,
    Person,
    TrainingRequirement,
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
        )

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
    swc_form = SendHomeworkForm(submit_name='swc-submit')
    dc_form = SendHomeworkForm(submit_name='dc-submit')

    # Add information about instructor training progress to request.user.
    request.user = Person.objects.annotate_with_instructor_eligibility() \
                                 .get(pk=request.user.pk)

    progresses = request.user.trainingprogress_set.filter(discarded=False)
    last_swc_homework = progresses.filter(
        requirement__name='SWC Homework').order_by('-created_at').first()
    request.user.swc_homework_in_evaluation = (
        last_swc_homework is not None and last_swc_homework.state == 'n')
    last_dc_homework = progresses.filter(
        requirement__name='DC Homework').order_by('-created_at').first()
    request.user.dc_homework_in_evaluation = (
        last_dc_homework is not None and last_dc_homework.state == 'n')

    # Add information about awarded instructor badges to request.user.
    request.user.is_swc_instructor = request.user.award_set.filter(
        badge__name='swc-instructor').exists()
    request.user.is_dc_instructor = request.user.award_set.filter(
        badge__name='dc-instructor').exists()

    if request.method == 'POST' and 'swc-submit' in request.POST:
        requirement = TrainingRequirement.objects.get(name='SWC Homework')
        progress = TrainingProgress(trainee=request.user,
                                    state='n',  # not-evaluated yet
                                    requirement=requirement)
        swc_form = SendHomeworkForm(data=request.POST, instance=progress,
                                    submit_name='swc-submit')
        dc_form = SendHomeworkForm(submit_name='dc-submit')

        if swc_form.is_valid():
            swc_form.save()
            messages.success(request, 'Your homework submission will be '
                                      'evaluated soon.')
            return redirect(reverse('training-progress'))

    elif request.method == 'POST' and 'dc-submit' in request.POST:
        requirement = TrainingRequirement.objects.get(name='DC Homework')
        progress = TrainingProgress(trainee=request.user,
                                    state='n',  # not-evaluated yet
                                    requirement=requirement)
        swc_form = SendHomeworkForm(submit_name='swc-submit')
        dc_form = SendHomeworkForm(data=request.POST, instance=progress,
                                    submit_name='dc-submit')

        if dc_form.is_valid():
            dc_form.save()
            messages.success(request, 'Your homework submission will be '
                                      'evaluated soon.')
            return redirect(reverse('training-progress'))

    else:  # GET request
        pass

    context = {
        'title': 'Your training progress',
        'swc_form': swc_form,
        'dc_form': dc_form,
    }
    return render(request, 'dashboard/training_progress.html', context)
