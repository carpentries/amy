from django.contrib import messages
from django.db.models import (
    Case,
    When,
    IntegerField,
    Count,
    F,
    Sum,
    Prefetch,
)
from django.shortcuts import render, redirect
from django.urls import reverse_lazy

from trainings.filters import (
    TraineeFilter,
)
from trainings.forms import (
    TrainingProgressForm,
    BulkAddTrainingProgressForm,
    BulkDiscardProgressesForm,
)
from workshops.base_views import (
    AMYCreateView,
    AMYUpdateView,
    AMYDeleteView,
    AMYListView,
    RedirectSupportMixin,
    PrepopulationSupportMixin,
)
from workshops.models import (
    Badge,
    Event,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)
from workshops.util import (
    get_pagination_items,
    admin_required,
    OnlyForAdminsMixin,
)


class AllTrainings(OnlyForAdminsMixin, AMYListView):
    context_object_name = 'all_trainings'
    template_name = 'trainings/all_trainings.html'
    queryset = Event.objects.filter(tags__name='TTT').annotate(
        trainees=Count(Case(When(task__role__name='learner',
                                 then=F('task__person__id')),
                            output_field=IntegerField()),
                       distinct=True),
        finished=Count(Case(When(task__role__name='learner',
                                 task__person__badges__in=Badge.objects.instructor_badges(),
                                 then=F('task__person__id')),
                            output_field=IntegerField()),
                       distinct=True),
    ).exclude(trainees=0).order_by('-start')
    title = 'All Instructor Trainings'


# ------------------------------------------------------------
# Instructor Training related views

class TrainingProgressCreate(RedirectSupportMixin,
                             PrepopulationSupportMixin,
                             OnlyForAdminsMixin,
                             AMYCreateView):
    model = TrainingProgress
    form_class = TrainingProgressForm
    populate_fields = ['trainee']

    def get_initial(self):
        initial = super().get_initial()
        initial['evaluated_by'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'].helper = context['form'].create_helper
        return context


class TrainingProgressUpdate(RedirectSupportMixin, OnlyForAdminsMixin,
                             AMYUpdateView):
    model = TrainingProgress
    form_class = TrainingProgressForm
    template_name = 'trainings/trainingprogress_form.html'


class TrainingProgressDelete(RedirectSupportMixin, OnlyForAdminsMixin,
                             AMYDeleteView):
    model = TrainingProgress
    success_url = reverse_lazy('all_trainees')


@admin_required
def all_trainees(request):
    filter = TraineeFilter(
        request.GET,
        queryset=Person.objects
            .annotate_with_instructor_eligibility()
            .defer('notes')  # notes are too large, so we defer them
            .prefetch_related(
                Prefetch('task_set',
                         to_attr='training_tasks',
                         queryset=Task.objects.filter(role__name='learner',
                                                      event__tags__name='TTT')),
                'training_tasks__event',
                'trainingrequest_set',
                'trainingprogress_set',
                'trainingprogress_set__requirement',
                'trainingprogress_set__evaluated_by',
            ).annotate(
                is_swc_instructor=Sum(Case(When(badges__name='swc-instructor',
                                                then=1),
                                           default=0,
                                           output_field=IntegerField())),
                is_dc_instructor=Sum(Case(When(badges__name='dc-instructor',
                                               then=1),
                                          default=0,
                                          output_field=IntegerField())),
                is_lc_instructor=Sum(Case(When(badges__name='lc-instructor',
                                               then=1),
                                          default=0,
                                          output_field=IntegerField())),
            )
    )
    trainees = get_pagination_items(request, filter.qs)

    if request.method == 'POST' and 'discard' in request.POST:
        # Bulk discard progress of selected trainees
        form = BulkAddTrainingProgressForm()
        discard_form = BulkDiscardProgressesForm(request.POST)
        if discard_form.is_valid():
            for trainee in discard_form.cleaned_data['trainees']:
                TrainingProgress.objects.filter(trainee=trainee)\
                                        .update(discarded=True)
            messages.success(request, 'Successfully discarded progress of '
                                      'all selected trainees.')

            # Raw uri contains GET parameters from django filters. We use it
            # to preserve filter settings.
            return redirect(request.get_raw_uri())

    elif request.method == 'POST' and 'submit' in request.POST:
        # Bulk add progress to selected trainees
        instance = TrainingProgress(evaluated_by=request.user)
        form = BulkAddTrainingProgressForm(request.POST, instance=instance)
        discard_form = BulkDiscardProgressesForm()
        if form.is_valid():
            for trainee in form.cleaned_data['trainees']:
                TrainingProgress.objects.create(
                    trainee=trainee,
                    evaluated_by=request.user,
                    requirement=form.cleaned_data['requirement'],
                    state=form.cleaned_data['state'],
                    discarded=False,
                    event=form.cleaned_data['event'],
                    url=form.cleaned_data['url'],
                    notes=form.cleaned_data['notes'],
                )
            messages.success(request, 'Successfully changed progress of '
                                      'all selected trainees.')

            return redirect(request.get_raw_uri())

    else:  # GET request
        # If the user filters by training, we want to set initial values for
        # "requirement" and "training" fields.
        training_id = request.GET.get('training', None) or None
        try:
            initial = {
                'event': Event.objects.get(pk=training_id),
                'requirement': TrainingRequirement.objects.get(name='Training')
            }
        except Event.DoesNotExist:  # or there is no `training` GET parameter
            initial = None

        form = BulkAddTrainingProgressForm(initial=initial)
        discard_form = BulkDiscardProgressesForm()

    context = {'title': 'Trainees',
               'all_trainees': trainees,
               'swc': Badge.objects.get(name='swc-instructor'),
               'dc': Badge.objects.get(name='dc-instructor'),
               'lc': Badge.objects.get(name='lc-instructor'),
               'filter': filter,
               'form': form,
               'discard_form': discard_form}
    return render(request, 'trainings/all_trainees.html', context)
