from django.contrib import messages
from django.db.models import Case, Count, F, IntegerField, Prefetch, Sum, When
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from trainings.filters import TraineeFilter
from trainings.forms import (
    BulkAddTrainingProgressForm,
    BulkDiscardProgressesForm,
    TrainingProgressForm,
)
from workshops.base_views import (
    AMYCreateView,
    AMYDeleteView,
    AMYListView,
    AMYUpdateView,
    PrepopulationSupportMixin,
    RedirectSupportMixin,
)
from workshops.models import (
    Badge,
    Event,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)
from workshops.utils.access import OnlyForAdminsMixin, admin_required
from workshops.utils.pagination import get_pagination_items


class AllTrainings(OnlyForAdminsMixin, AMYListView):
    context_object_name = "all_trainings"
    template_name = "trainings/all_trainings.html"
    queryset = (
        Event.objects.filter(tags__name="TTT")
        .annotate(
            trainees=Count(
                Case(
                    When(task__role__name="learner", then=F("task__person__id")),
                    output_field=IntegerField(),
                ),
                distinct=True,
            ),
            finished=Count(
                Case(
                    When(
                        task__role__name="learner",
                        task__person__badges__in=Badge.objects.instructor_badges(),
                        then=F("task__person__id"),
                    ),
                    output_field=IntegerField(),
                ),
                distinct=True,
            ),
        )
        .exclude(trainees=0)
        .order_by("-start")
    )
    title = "All Instructor Trainings"


# ------------------------------------------------------------
# Instructor Training related views


class TrainingProgressCreate(
    RedirectSupportMixin, PrepopulationSupportMixin, OnlyForAdminsMixin, AMYCreateView
):
    model = TrainingProgress
    form_class = TrainingProgressForm
    populate_fields = ["trainee"]

    def get_initial(self):
        initial = super().get_initial()
        initial["evaluated_by"] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"].helper = context["form"].create_helper
        return context


class TrainingProgressUpdate(RedirectSupportMixin, OnlyForAdminsMixin, AMYUpdateView):
    model = TrainingProgress
    form_class = TrainingProgressForm
    template_name = "trainings/trainingprogress_form.html"


class TrainingProgressDelete(RedirectSupportMixin, OnlyForAdminsMixin, AMYDeleteView):
    model = TrainingProgress
    success_url = reverse_lazy("all_trainees")


def all_trainees_queryset():
    return (
        Person.objects.annotate_with_instructor_eligibility()
        .prefetch_related(
            Prefetch(
                "task_set",
                to_attr="training_tasks",
                queryset=Task.objects.filter(
                    role__name="learner", event__tags__name="TTT"
                ),
            ),
            "training_tasks__event",
            "trainingrequest_set",
            "trainingprogress_set",
            "trainingprogress_set__requirement",
            "trainingprogress_set__evaluated_by",
        )
        .annotate(
            is_instructor=Sum(
                Case(
                    When(badges__name=Badge.SINGLE_INSTRUCTOR_BADGE, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
        )
        .order_by("family", "personal")
    )


@admin_required
def all_trainees(request):
    filter = TraineeFilter(
        request.GET,
        queryset=all_trainees_queryset(),
    )
    trainees = get_pagination_items(request, filter.qs)

    if request.method == "POST" and "discard" in request.POST:
        # Bulk discard progress of selected trainees
        form = BulkAddTrainingProgressForm()
        discard_form = BulkDiscardProgressesForm(request.POST)
        if discard_form.is_valid():
            for trainee in discard_form.cleaned_data["trainees"]:
                TrainingProgress.objects.filter(trainee=trainee).update(discarded=True)
            messages.success(
                request, "Successfully discarded progress of all selected trainees."
            )

            # Raw uri contains GET parameters from django filters. We use it
            # to preserve filter settings.
            return redirect(request.get_raw_uri())

    elif request.method == "POST" and "submit" in request.POST:
        # Bulk add progress to selected trainees
        instance = TrainingProgress(evaluated_by=request.user)
        form = BulkAddTrainingProgressForm(request.POST, instance=instance)
        discard_form = BulkDiscardProgressesForm()
        if form.is_valid():
            for trainee in form.cleaned_data["trainees"]:
                TrainingProgress.objects.create(
                    trainee=trainee,
                    evaluated_by=request.user,
                    requirement=form.cleaned_data["requirement"],
                    state=form.cleaned_data["state"],
                    discarded=False,
                    event=form.cleaned_data["event"],
                    url=form.cleaned_data["url"],
                    notes=form.cleaned_data["notes"],
                )
            messages.success(
                request, "Successfully changed progress of all selected trainees."
            )

            return redirect(request.get_raw_uri())

    else:  # GET request
        # If the user filters by training, we want to set initial values for
        # "requirement" and "training" fields.
        training_id = request.GET.get("training", None) or None
        try:
            initial = {
                "event": Event.objects.get(pk=training_id),
                "requirement": TrainingRequirement.objects.get(name="Training"),
            }
        except Event.DoesNotExist:  # or there is no `training` GET parameter
            initial = None

        form = BulkAddTrainingProgressForm(initial=initial)
        discard_form = BulkDiscardProgressesForm()

    context = {
        "title": "Trainees",
        "all_trainees": trainees,
        "filter": filter,
        "form": form,
        "discard_form": discard_form,
    }
    return render(request, "trainings/all_trainees.html", context)
