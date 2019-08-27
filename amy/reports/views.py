import datetime

from django.contrib import messages
from django.db.models import (
    Case,
    When,
    Value,
    IntegerField,
    Count,
    Q,
    F,
    Prefetch,
)
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse

from api.filters import (
    InstructorsOverTimeFilter,
    WorkshopsOverTimeFilter,
    LearnersOverTimeFilter,
)
from api.views import ReportsViewSet
from fiscal.filters import MembershipTrainingsFilter
from reports.forms import (
    DebriefForm,
    AllActivityOverTimeForm,
)
from workshops.models import (
    Badge,
    Event,
    Person,
    Role,
    Membership,
    Tag,
    Task,
    TrainingRequest,
)
from workshops.util import (
    assignment_selection,
    get_pagination_items,
    admin_required,
)


@admin_required
def instructors_by_date(request):
    '''Show who taught between begin_date and end_date.'''

    form = DebriefForm()
    if 'begin_date' in request.GET and 'end_date' in request.GET:
        form = DebriefForm(request.GET)

    if form.is_valid():
        start_date = form.cleaned_data['begin_date']
        end_date = form.cleaned_data['end_date']
        mode = form.cleaned_data['mode']
        rvs = ReportsViewSet()
        tasks = rvs.instructors_by_time_queryset(
            start_date, end_date,
            only_TTT=(mode == 'TTT'),
            only_non_TTT=(mode == 'nonTTT'),
        )
        emails = tasks.filter(person__may_contact=True) \
                      .exclude(person__email=None) \
                      .values_list('person__email', flat=True)
    else:
        start_date = None
        end_date = None
        tasks = None
        emails = None
        mode = 'all'

    context = {
        'title': 'List of instructors by time period',
        'form': form,
        'all_tasks': tasks,
        'emails': emails,
        'start_date': start_date,
        'end_date': end_date,
        'mode': mode,
    }
    return render(request, 'reports/instructors_by_date.html', context)


@admin_required
def workshops_over_time(request):
    '''Export JSON of count of workshops vs. time.'''
    endpoint = '{}?{}'.format(reverse('api:reports-workshops-over-time'),
                              request.GET.urlencode())
    context = {
        'api_endpoint': endpoint,
        'filter': WorkshopsOverTimeFilter(request.GET),
        'title': 'Workshops over time',
    }
    return render(request, 'reports/time_series.html', context)


@admin_required
def learners_over_time(request):
    '''Export JSON of count of learners vs. time.'''
    endpoint = '{}?{}'.format(reverse('api:reports-learners-over-time'),
                              request.GET.urlencode())
    context = {
        'api_endpoint': endpoint,
        'filter': LearnersOverTimeFilter(request.GET),
        'title': 'Learners over time',
    }
    return render(request, 'reports/time_series.html', context)


@admin_required
def instructors_over_time(request):
    '''Export JSON of count of instructors vs. time.'''
    endpoint = '{}?{}'.format(reverse('api:reports-instructors-over-time'),
                              request.GET.urlencode())
    context = {
        'api_endpoint': endpoint,
        'filter': InstructorsOverTimeFilter(request.GET),
        'title': 'Instructors over time',
    }
    return render(request, 'reports/time_series.html', context)


@admin_required
def instructor_num_taught(request):
    '''Export JSON of how often instructors have taught.'''
    context = {
        'api_endpoint': reverse('api:reports-instructor-num-taught'),
        'title': 'Frequency of Instruction',
    }
    return render(request, 'reports/instructor_num_taught.html', context)


@admin_required
def all_activity_over_time(request):
    """Display number of workshops (of differend kinds), instructors and
    learners over some specific period of time."""

    if 'submit' in request.GET:
        form = AllActivityOverTimeForm(request.GET)

        if form.is_valid():
            data = ReportsViewSet().get_all_activity_over_time(
                start=form.cleaned_data['start'],
                end=form.cleaned_data['end'],
            )
        else:
            data = None
    else:
        form = AllActivityOverTimeForm(initial={
            'start': datetime.date.today() - datetime.timedelta(days=365),
            'end': datetime.date.today(),
        })
        data = None

    context = {
        'title': 'All activity over time',
        'form': form,
        'data': data,
    }
    return render(request, 'reports/all_activity_over_time.html', context)


@admin_required
def membership_trainings_stats(request):
    """Display basic statistics for memberships and instructor trainings."""
    # today = datetime.date.today()
    data = (
            Membership.objects
            # .filter(agreement_end__gte=today, agreement_start__lte=today)
            .select_related('organization')
            .prefetch_related('task_set')
            .annotate(
                instructor_training_seats_total=(
                    F('seats_instructor_training') +
                    F('additional_instructor_training_seats')
                ),
                instructor_training_seats_utilized=(
                    Count('task', filter=Q(task__role__name='learner'))
                ),
                instructor_training_seats_remaining=(
                    F('seats_instructor_training') +
                    F('additional_instructor_training_seats') -
                    Count('task', filter=Q(task__role__name='learner'))
                ),
            )
    )

    filter_ = MembershipTrainingsFilter(request.GET, data)
    paginated = get_pagination_items(request, filter_.qs)
    context = {
        'title': 'Membership trainings statistics',
        'data': paginated,
        'filter': filter_,
    }
    return render(request, 'reports/membership_trainings_stats.html',
                  context)


@admin_required
def workshop_issues(request):
    '''Display workshops in the database whose records need attention.'''

    events = Event.objects.active().past_events().annotate(
        num_instructors=Count(
            Case(
                When(
                    task__role__name='instructor',
                    then=Value(1)
                ),
                output_field=IntegerField()
            )
        )
    ).attendance().order_by('-start')

    no_attendance = Q(attendance=None) | Q(attendance=0)
    no_location = (Q(country=None) |
                   Q(venue=None) | Q(venue__exact='') |
                   Q(address=None) | Q(address__exact='') |
                   Q(latitude=None) | Q(longitude=None))
    bad_dates = Q(start__gt=F('end'))

    events = events.filter(
        (no_attendance & ~Q(tags__name='unresponsive')) |
        no_location |
        bad_dates |
        Q(num_instructors=0)
    ).prefetch_related('task_set', 'task_set__person')

    events = events.prefetch_related(Prefetch(
        'task_set',
        to_attr='contacts',
        queryset=Task.objects.select_related('person').filter(
            # we only want hosts, organizers and instructors
            Q(role__name='host') | Q(role__name='organizer') |
            Q(role__name='instructor')
        ).filter(person__may_contact=True)
        .exclude(Q(person__email='') | Q(person__email=None))
    ))

    assigned_to, is_admin = assignment_selection(request)

    if assigned_to == 'me':
        events = events.filter(assigned_to=request.user)

    elif assigned_to == 'noone':
        events = events.filter(assigned_to=None)

    elif assigned_to == 'all':
        # no filtering
        pass

    else:
        # no filtering
        pass

    events = events.annotate(
        missing_attendance=Case(
            When(no_attendance, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        missing_location=Case(
            When(no_location, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        bad_dates=Case(
            When(bad_dates, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
    )

    context = {
        'title': 'Workshops with Issues',
        'events': events,
        'is_admin': is_admin,
        'assigned_to': assigned_to,
    }
    return render(request, 'reports/workshop_issues.html', context)


@admin_required
def instructor_issues(request):
    '''Display instructors in the database who need attention.'''

    # Everyone who has a badge but needs attention.
    instructor_badges = Badge.objects.instructor_badges()
    instructors = Person.objects.filter(badges__in=instructor_badges) \
                                .filter(airport__isnull=True)

    # Everyone who's been in instructor training but doesn't yet have a badge.
    learner = Role.objects.get(name='learner')
    ttt = Tag.objects.get(name='TTT')
    stalled = Tag.objects.get(name='stalled')
    trainees = Task.objects \
        .filter(event__tags__in=[ttt], role=learner) \
        .exclude(person__badges__in=instructor_badges) \
        .order_by('person__family', 'person__personal', 'event__start') \
        .select_related('person', 'event')

    pending_instructors = trainees.exclude(event__tags=stalled)
    pending_instructors_person_ids = pending_instructors.values_list(
        'person__pk', flat=True,
    )

    stalled_instructors = trainees \
        .filter(event__tags=stalled) \
        .exclude(person__id__in=pending_instructors_person_ids)

    context = {
        'title': 'Instructors with Issues',
        'instructors': instructors,
        'pending': pending_instructors,
        'stalled': stalled_instructors,
    }
    return render(request, 'reports/instructor_issues.html', context)


@admin_required
def duplicate_persons(request):
    """Find possible duplicates amongst persons.

    Criteria for persons:
    * switched personal/family names
    * same name on different people."""

    names_normal = set(
        Person.objects.duplication_review_expired()
                      .values_list('personal', 'family')
                    )
    names_switched = set(
        Person.objects.duplication_review_expired()
                      .values_list('family', 'personal')
    )
    names = names_normal & names_switched  # intersection

    switched_criteria = Q(id=0)
    # empty query results if names is empty
    for personal, family in names:
        # get people who appear in `names`
        switched_criteria |= (Q(personal=personal) & Q(family=family))

    switched_persons = Person.objects.duplication_review_expired()\
                                     .filter(switched_criteria) \
                                     .order_by('email')

    duplicate_names = Person.objects.duplication_review_expired() \
                                    .values('personal', 'family') \
                                    .order_by('family', 'personal') \
                                    .annotate(count_id=Count('id')) \
                                    .filter(count_id__gt=1)

    duplicate_criteria = Q(id=0)
    for name in duplicate_names:
        # get people who appear in `names`
        duplicate_criteria |= (Q(personal=name['personal']) &
                               Q(family=name['family']))

    duplicate_persons = Person.objects.duplication_review_expired() \
                                      .filter(duplicate_criteria) \
                                      .order_by('family', 'personal', 'email')

    context = {
        'title': 'Possible duplicate persons',
        'switched_persons': switched_persons,
        'duplicate_persons': duplicate_persons,
    }

    return render(request, 'reports/duplicate_persons.html', context)


@admin_required
def review_duplicate_persons(request):
    if request.method == 'POST' and 'person_id' in request.POST:
        ids = request.POST.getlist('person_id')
        now = timezone.now()
        number = Person.objects.filter(id__in=ids) \
                               .update(duplication_reviewed_on=now)
        messages.success(
            request,
            'Successfully marked {} persons as reviewed.'.format(number)
        )

    else:
        messages.warning(request, 'Wrong request or request data missing.')

    return redirect(reverse('duplicate_persons'))


@admin_required
def duplicate_training_requests(request):
    """Find possible duplicates amongst training requests.

    Criteria:
    * the same name
    * the same email.
    """
    names = (
        TrainingRequest.objects
        .values('personal', 'family')
        .order_by('family', 'personal')
        .annotate(count_id=Count('id'))
        .filter(count_id__gt=1)
    )
    duplicate_names_criteria = Q(id=0)
    for name in names:
        duplicate_names_criteria |= (Q(personal=name['personal']) &
                                     Q(family=name['family']))

    emails = (
        TrainingRequest.objects
        .values_list('email', flat=True)
        .order_by('family', 'personal')
        .annotate(count_id=Count('id'))
        .filter(count_id__gt=1)
    )
    duplicate_emails_criteria = Q(id=0)
    for email in emails:
        duplicate_emails_criteria |= Q(email=email)

    duplicate_names = TrainingRequest.objects \
                                     .filter(duplicate_names_criteria) \
                                     .order_by('family', 'personal')
    duplicate_emails = TrainingRequest.objects \
                                      .filter(duplicate_emails_criteria) \
                                      .order_by('email')

    context = {
        'title': 'Possible duplicate training requests',
        'duplicate_names': duplicate_names,
        'duplicate_emails': duplicate_emails,
    }

    return render(request, 'reports/duplicate_training_requests.html',
                  context)
