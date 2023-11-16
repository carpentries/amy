from datetime import datetime
from functools import partial, reduce
import logging
import operator
import re

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.http import JsonResponse
from django.http.response import Http404
from django.urls import path
from django_select2.views import AutoResponseView

from fiscal.models import MembershipPersonRole
from workshops import models
from workshops.utils.access import LoginNotRequiredMixin, OnlyForAdminsNoRedirectMixin

logger = logging.getLogger("amy")


class ExtensibleAutoResponseView(AutoResponseView):
    def get(self, request, *args, **kwargs):
        self.widget = self.get_widget_or_404()
        self.term = kwargs.get("term", request.GET.get("term", ""))
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return JsonResponse(
            {
                "results": self.parse_results(context["object_list"]),
                "more": context["page_obj"].has_next(),
            }
        )

    def parse_results(self, object_list):
        return [
            {"text": self.widget.label_from_instance(obj), "id": obj.pk}
            for obj in object_list
        ]


class TagLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        q = models.Tag.objects.all()
        if self.term:
            return q.filter(name__icontains=self.term)
        return q


class BadgeLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        q = models.Badge.objects.all()
        if self.term:
            return q.filter(
                Q(name__icontains=self.term) | Q(title__icontains=self.term)
            )
        return q


class LessonLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        q = models.Lesson.objects.all()
        if self.term:
            return q.filter(name__icontains=self.term)
        return q


class EventLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Event.objects.all()

        if self.term:
            results = results.filter(slug__icontains=self.term)

        return results


class EventLookupForAwardsView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Event.objects.all()

        # if awarding an Instructor badge, find relevant events this person attended
        person = self.request.GET.get("person")
        badge = self.request.GET.get("badge")
        if (
            person
            and badge
            and int(badge) == models.Badge.objects.get(name="instructor").pk
        ):
            learner_progresses = models.TrainingProgress.objects.filter(
                trainee__id=person,
                requirement__in=models.TrainingRequirement.objects.filter(
                    event_required=True
                ),
                state="p",
            )
            results = results.filter(trainingprogress__in=learner_progresses)

        if self.term:
            results = results.filter(slug__icontains=self.term)

        return results


class TTTEventLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Event.objects.ttt()

        # trainee is provided through the TrainingProgress creation views
        # for which learner tasks are relevant
        if trainee := self.request.GET.get("trainee"):
            learner_tasks = models.Task.objects.filter(
                role__name="learner", person__id=trainee
            )
            results = results.filter(task__in=learner_tasks)

        if self.term:
            results = results.filter(slug__icontains=self.term)

        return results


class OrganizationLookupView(OnlyForAdminsNoRedirectMixin, ExtensibleAutoResponseView):
    def get_queryset(self):
        results = models.Organization.objects.order_by("fullname")

        if self.term:
            results = results.filter(
                Q(domain__icontains=self.term) | Q(fullname__icontains=self.term)
            )

        return results

    def parse_results(self, object_list):
        return [
            {
                "fullname": obj.fullname,
                "text": self.widget.label_from_instance(obj),
                "id": obj.pk,
            }
            for obj in object_list
        ]


class AdministratorOrganizationLookupView(
    OnlyForAdminsNoRedirectMixin, AutoResponseView
):
    def get_queryset(self):
        results = models.Organization.objects.administrators()

        if self.term:
            results = results.filter(
                Q(domain__icontains=self.term) | Q(fullname__icontains=self.term)
            )

        return results


class MembershipLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Membership.objects.all()

        if self.term:
            # parse query into date
            try:
                date = datetime.strptime(self.term, "%Y-%m-%d").date()
            except ValueError:
                date = None

            # filter by membership name
            name = Q(name__icontains=self.term)

            # filter by organization name
            org_q = Q(organizations__domain__icontains=self.term) | Q(
                organizations__fullname__icontains=self.term
            )

            # filter by variant
            variant_q = Q(variant__icontains=self.term)

            if date:
                # filter by agreement date range
                agreement_q = Q(agreement_start__lte=date, agreement_end__gte=date)

                results = results.filter(
                    name | org_q | variant_q | agreement_q
                ).distinct()
            else:
                results = results.filter(name | org_q | variant_q).distinct()

        return results


class MemberRoleLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        q = models.MemberRole.objects.all()
        if self.term:
            return q.filter(
                Q(name__icontains=self.term) | Q(verbose_name__icontains=self.term)
            )
        return q


class MembershipPersonRoleLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        q = MembershipPersonRole.objects.all()
        if self.term:
            return q.filter(
                Q(name__icontains=self.term) | Q(verbose_name__icontains=self.term)
            )
        return q


class PersonLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Person.objects.all()

        if self.term:
            filters = [
                Q(personal__icontains=self.term),
                Q(family__icontains=self.term),
                Q(email__icontains=self.term),
                Q(secondary_email__icontains=self.term),
                Q(username__icontains=self.term),
            ]

            # split query into first and last names
            tokens = re.split(r"\s+", self.term)
            if len(tokens) == 2:
                name1, name2 = tokens
                complex_q = (
                    Q(personal__icontains=name1) & Q(family__icontains=name2)
                ) | (Q(personal__icontains=name2) & Q(family__icontains=name1))
                filters.append(complex_q)

            # this is brilliant: it applies OR to all search filters
            results = results.filter(reduce(operator.or_, filters))

        return results


class InstructorLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    """Lookup view for instructors using Community Roles approach (Instructor Role)."""

    def get_queryset(self):
        results = models.Person.objects.filter(
            communityrole__config__name="instructor"
        ).distinct()

        if self.term:
            filters = [
                Q(personal__icontains=self.term),
                Q(family__icontains=self.term),
                Q(email__icontains=self.term),
                Q(secondary_email__icontains=self.term),
                Q(username__icontains=self.term),
            ]

            # split query into first and last names
            tokens = re.split(r"\s+", self.term)
            if len(tokens) == 2:
                name1, name2 = tokens
                complex_q = (
                    Q(personal__icontains=name1) & Q(family__icontains=name2)
                ) | (Q(personal__icontains=name2) & Q(family__icontains=name1))
                filters.append(complex_q)

            results = results.filter(reduce(operator.or_, filters))

        return results


class AdminLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    """The same as PersonLookup, but allows only to select administrators.

    Administrator is anyone with superuser power or in "administrators" group.
    """

    def get_queryset(self):
        admin_group = Group.objects.get(name="administrators")
        results = models.Person.objects.filter(
            Q(is_superuser=True) | Q(groups__in=[admin_group])
        )

        if self.term:
            results = results.filter(
                Q(personal__icontains=self.term)
                | Q(family__icontains=self.term)
                | Q(email__icontains=self.term)
                | Q(secondary_email__icontains=self.term)
                | Q(username__icontains=self.term)
            )

        return results


class AirportLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Airport.objects.all()

        if self.term:
            results = results.filter(
                Q(iata__icontains=self.term) | Q(fullname__icontains=self.term)
            )

        return results


class LanguageLookupView(LoginNotRequiredMixin, AutoResponseView):
    def dispatch(self, request, *args, **kwargs):
        self.subtag = "subtag" in request.GET.keys()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        results = models.Language.objects.all()

        if self.term:
            results = results.filter(
                Q(name__icontains=self.term) | Q(subtag__icontains=self.term)
            )

            if self.subtag:
                return results.filter(subtag__iexact=self.term)

        results = results.annotate(person_count=Count("person")).order_by(
            "-person_count"
        )

        return results


class KnowledgeDomainLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.KnowledgeDomain.objects.all()

        if self.term:
            results = results.filter(Q(name__icontains=self.term))

        results = results.annotate(person_count=Count("person")).order_by(
            "-person_count"
        )

        return results


class TrainingRequestLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    """The same as PersonLookup, but allows only to select administrators.

    Administrator is anyone with superuser power or in "administrators" group.
    """

    def get_queryset(self):
        results = models.TrainingRequest.objects.all()

        if self.term:
            # search for name if two words provided
            tok = re.split(r"\s+", self.term)
            if len(tok) == 2:
                name_q = Q(personal__icontains=tok[0], family__icontains=tok[1]) | Q(
                    personal__icontains=tok[1], family__icontains=tok[0]
                )
            else:
                # empty Q
                name_q = Q(id=0)

            results = results.filter(
                Q(personal__icontains=self.term)
                | Q(family__icontains=self.term)
                | Q(email__icontains=self.term)
                | Q(secondary_email__icontains=self.term)
                | name_q
            )

        return results


class AwardLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Award.objects.all()

        if badge := self.request.GET.get("badge"):
            results = results.filter(badge__pk=badge)

        if person := self.request.GET.get("person"):
            results = results.filter(person__pk=person)

        if self.term:
            results = results.filter(
                Q(person__personal__icontains=self.term)
                | Q(person__middle__icontains=self.term)
                | Q(person__family__icontains=self.term)
                | Q(person__email__icontains=self.term)
                | Q(badge__name__icontains=self.term)
            )

        return results


class GenericObjectLookupView(
    LoginRequiredMixin, UserPassesTestMixin, AutoResponseView
):
    raise_exception = True  # prevent redirect to login page on unauthenticated user

    def get_test_func(self):
        content_type = self.request.GET.get("content_type", "")
        return partial(self.test_func, content_type=content_type)

    def test_func(self, content_type: str):
        # Get the ContentType.
        try:
            self.content_type = ContentType.objects.get(pk=int(content_type))
        except (ContentType.DoesNotExist, ValueError):
            self.content_type = None
            logger.error(
                "GenericObjectLookup tried to look up non-existing ContentType "
                f"pk={content_type}"
            )
            return False

        # Find "view" permission name for model of type ContentType.
        action = "view"
        codename = f"{action}_{self.content_type.model}"
        # Build permission name. The same way is used in for example ModelAdmin.
        permission_name = f"{self.content_type.app_label}.{codename}"

        # Check is user has view permissions for that ContentType.
        return self.request.user.has_perm(permission_name)

    def get_queryset(self):
        if not self.content_type:
            return QuerySet()

        try:
            return self.content_type.model_class()._default_manager.all()
        except AttributeError as e:
            logger.error(
                f"ContentType {self.content_type} may be stale "
                f"(model class doesn't exist). Error: {e}"
            )
            raise Http404("ContentType not found.")

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        return JsonResponse(
            {
                "results": [
                    {
                        "text": str(obj),
                        "id": obj.pk,
                    }
                    for obj in self.object_list
                ],
            }
        )


urlpatterns = [
    path("tags/", TagLookupView.as_view(), name="tag-lookup"),
    path("badges/", BadgeLookupView.as_view(), name="badge-lookup"),
    path("lessons/", LessonLookupView.as_view(), name="lesson-lookup"),
    path("events/", EventLookupView.as_view(), name="event-lookup"),
    path(
        "events_for_awards/",
        EventLookupForAwardsView.as_view(),
        name="event-lookup-for-awards",
    ),
    path("ttt_events/", TTTEventLookupView.as_view(), name="ttt-event-lookup"),
    path(
        "organizations/", OrganizationLookupView.as_view(), name="organization-lookup"
    ),
    path(
        "admin_orgs/",
        AdministratorOrganizationLookupView.as_view(),
        name="administrator-org-lookup",
    ),
    path("memberships/", MembershipLookupView.as_view(), name="membership-lookup"),
    path("member-roles/", MemberRoleLookupView.as_view(), name="memberrole-lookup"),
    path(
        "membership-person-roles/",
        MembershipPersonRoleLookupView.as_view(),
        name="membershippersonrole-lookup",
    ),
    path("persons/", PersonLookupView.as_view(), name="person-lookup"),
    path("admins/", AdminLookupView.as_view(), name="admin-lookup"),
    # uses community role
    path("instructors/", InstructorLookupView.as_view(), name="instructor-lookup"),
    path("airports/", AirportLookupView.as_view(), name="airport-lookup"),
    path("languages/", LanguageLookupView.as_view(), name="language-lookup"),
    path(
        "knowledge_domains/",
        KnowledgeDomainLookupView.as_view(),
        name="knowledge-domains-lookup",
    ),
    path(
        "training_requests/",
        TrainingRequestLookupView.as_view(),
        name="trainingrequest-lookup",
    ),
    path("awards/", AwardLookupView.as_view(), name="award-lookup"),
    path("generic/", GenericObjectLookupView.as_view(), name="generic-object-lookup"),
]
