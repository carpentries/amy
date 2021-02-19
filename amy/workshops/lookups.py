from functools import reduce
from datetime import datetime
import operator
import re

from django_select2.views import AutoResponseView
from django.http import JsonResponse
from django.contrib.auth.models import Group
from django.conf.urls import url
from django.db.models import Q, Count

from fiscal.models import MembershipPersonRole
from workshops import models
from workshops.util import OnlyForAdminsNoRedirectMixin, LoginNotRequiredMixin


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


class TTTEventLookupView(OnlyForAdminsNoRedirectMixin, AutoResponseView):
    def get_queryset(self):
        results = models.Event.objects.filter(tags__name="TTT")

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

            # filter by organization name
            org_q = Q(organization__domain__icontains=self.term) | Q(
                organization__fullname__icontains=self.term
            )

            # filter by variant
            variant_q = Q(variant__icontains=self.term)

            if date:
                # filter by agreement date range
                agreement_q = Q(agreement_start__lte=date, agreement_end__gte=date)

                results = results.filter(org_q | variant_q | agreement_q)
            else:
                results = results.filter(org_q | variant_q)

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



class KnowledgeDomainLookupView(LoginNotRequiredMixin, AutoResponseView):
    def dispatch(self, request, *args, **kwargs):
        self.subtag = "subtag" in request.GET.keys()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        results = models.KnowledgeDomain.objects.all()

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


urlpatterns = [
    url(r"^tags/$", TagLookupView.as_view(), name="tag-lookup"),
    url(r"^badges/$", BadgeLookupView.as_view(), name="badge-lookup"),
    url(r"^lessons/$", LessonLookupView.as_view(), name="lesson-lookup"),
    url(r"^events/$", EventLookupView.as_view(), name="event-lookup"),
    url(r"^ttt_events/$", TTTEventLookupView.as_view(), name="ttt-event-lookup"),
    url(
        r"^organizations/$",
        OrganizationLookupView.as_view(),
        name="organization-lookup",
    ),
    url(
        r"^admin_orgs/$",
        AdministratorOrganizationLookupView.as_view(),
        name="administrator-org-lookup",
    ),
    url(r"^memberships/$", MembershipLookupView.as_view(), name="membership-lookup"),
    url(r"^member-roles/$", MemberRoleLookupView.as_view(), name="memberrole-lookup"),
    url(
        r"^membership-person-roles/$",
        MembershipPersonRoleLookupView.as_view(),
        name="membershippersonrole-lookup",
    ),
    url(r"^persons/$", PersonLookupView.as_view(), name="person-lookup"),
    url(r"^admins/$", AdminLookupView.as_view(), name="admin-lookup"),
    url(r"^airports/$", AirportLookupView.as_view(), name="airport-lookup"),
    url(r"^languages/$", LanguageLookupView.as_view(), name="language-lookup"),
    url(r"^knowledge_domains/$", KnowledgeDomainLookupView.as_view(), name="knowledge-domains-lookup"),
    url(
        r"^training_requests/$",
        TrainingRequestLookupView.as_view(),
        name="trainingrequest-lookup",
    ),
]
