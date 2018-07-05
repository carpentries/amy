from functools import reduce
import operator
import re

from dal import autocomplete
from django.contrib.auth.models import Group
from django.conf.urls import url
from django.db.models import Q, Count

from workshops import models
from workshops.util import OnlyForAdminsNoRedirectMixin, LoginNotRequiredMixin


class EventLookupView(OnlyForAdminsNoRedirectMixin,
                      autocomplete.Select2QuerySetView):
    def get_queryset(self):
        results = models.Event.objects.all()

        if self.q:
            results = results.filter(slug__icontains=self.q)

        return results


class TTTEventLookupView(OnlyForAdminsNoRedirectMixin,
                         autocomplete.Select2QuerySetView):
    def get_queryset(self):
        results = models.Event.objects.filter(tags__name='TTT')

        if self.q:
            results = results.filter(slug__icontains=self.q)

        return results


class OrganizationLookupView(OnlyForAdminsNoRedirectMixin,
                             autocomplete.Select2QuerySetView):
    def get_queryset(self):
        results = models.Organization.objects.all()

        if self.q:
            results = results.filter(
                Q(domain__icontains=self.q) | Q(fullname__icontains=self.q)
            )

        return results


class PersonLookupView(OnlyForAdminsNoRedirectMixin,
                       autocomplete.Select2QuerySetView):
    def get_queryset(self):
        results = models.Person.objects.all()

        if self.q:
            filters = [
                Q(personal__icontains=self.q),
                Q(family__icontains=self.q),
                Q(email__icontains=self.q),
                Q(username__icontains=self.q)
            ]

            # split query into first and last names
            tokens = re.split('\s+', self.q)
            if len(tokens) == 2:
                name1, name2 = tokens
                complex_q = (
                    Q(personal__icontains=name1) & Q(family__icontains=name2)
                ) | (
                    Q(personal__icontains=name2) & Q(family__icontains=name1)
                )
                filters.append(complex_q)

            # this is brilliant: it applies OR to all search filters
            results = results.filter(reduce(operator.or_, filters))

        return results


class AdminLookupView(OnlyForAdminsNoRedirectMixin,
                      autocomplete.Select2QuerySetView):
    """The same as PersonLookup, but allows only to select administrators.

    Administrator is anyone with superuser power or in "administrators" group.
    """

    def get_queryset(self):
        admin_group = Group.objects.get(name='administrators')
        results = models.Person.objects.filter(
            Q(is_superuser=True) | Q(groups__in=[admin_group])
        )

        if self.q:
            results = results.filter(
                Q(personal__icontains=self.q) |
                Q(family__icontains=self.q) |
                Q(email__icontains=self.q) |
                Q(username__icontains=self.q)
            )

        return results


class AirportLookupView(OnlyForAdminsNoRedirectMixin,
                        autocomplete.Select2QuerySetView):
    def get_queryset(self):
        results = models.Airport.objects.all()

        if self.q:
            results = results.filter(
                Q(iata__icontains=self.q) | Q(fullname__icontains=self.q)
            )

        return results


class LanguageLookupView(LoginNotRequiredMixin,
                         autocomplete.Select2QuerySetView):
    def dispatch(self, request, *args, **kwargs):
        self.subtag = 'subtag' in request.GET.keys()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        results = models.Language.objects.all()

        if self.q:
            results = results.filter(
                Q(name__icontains=self.q) | Q(subtag__icontains=self.q)
            )

            if self.subtag:
                return results.filter(subtag__iexact=self.q)

        results = results.annotate(person_count=Count('person')) \
                         .order_by('-person_count')

        return results


# trainees lookup?


urlpatterns = [
    url(r'^events/$', EventLookupView.as_view(), name='event-lookup'),
    url(r'^ttt_events/$', TTTEventLookupView.as_view(), name='ttt-event-lookup'),
    url(r'^organizations/$', OrganizationLookupView.as_view(), name='organization-lookup'),
    url(r'^persons/$', PersonLookupView.as_view(), name='person-lookup'),
    url(r'^admins/$', AdminLookupView.as_view(), name='admin-lookup'),
    url(r'^airports/$', AirportLookupView.as_view(), name='airport-lookup'),
    url(r'^languages/$', LanguageLookupView.as_view(), name='language-lookup'),
]
