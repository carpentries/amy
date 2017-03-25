from functools import reduce
import operator
import re

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q, Count

from github import Github
from selectable.base import ModelLookup, LookupBase
from selectable.registry import registry

from workshops import models
from workshops.util import lookup_only_for_admins


class GitHubUserLookup(LookupBase):
    gh = Github(settings.GITHUB_API_TOKEN, per_page=10)

    def get_query(self, request, username):
        users = self.gh.search_users(username).get_page(0)
        return [user.login for user in users]


@lookup_only_for_admins
class EventLookup(ModelLookup):
    model = models.Event
    search_fields = ('slug__icontains', )


@lookup_only_for_admins
class TTTEventLookup(ModelLookup):
    model = models.Event
    search_fields = ('slug__icontains', )
    filters = {
        'tags__name': 'TTT',
    }


@lookup_only_for_admins
class OrganizationLookup(ModelLookup):
    model = models.Organization
    search_fields = (
        'domain__icontains',
        'fullname__icontains'
    )


@lookup_only_for_admins
class PersonLookup(ModelLookup):
    model = models.Person
    search_fields = (
        'personal__icontains',
        'family__icontains',
        'email__icontains',
        'username__icontains'
    )

    def get_query(self, request, term):
        """Override this method to allow for additional lookup method: """
        # original code from selectable.base.ModelLookup.get_query:
        qs = self.get_queryset()
        if term:
            search_filters = []
            if self.search_fields:
                for field in self.search_fields:
                    search_filters.append(Q(**{field: term}))

            # tokenizing part
            tokens = re.split('\s+', term)
            if len(tokens) == 2:
                name1, name2 = tokens
                complex_q = (
                    Q(personal__icontains=name1) & Q(family__icontains=name2)
                ) | (
                    Q(personal__icontains=name2) & Q(family__icontains=name1)
                )
                search_filters.append(complex_q)

            # this is brilliant: it applies OR to all search filters
            qs = qs.filter(reduce(operator.or_, search_filters))

        return qs


@lookup_only_for_admins
class AdminLookup(ModelLookup):
    """The same as PersonLookup, but allows only to select administrators.

    Administrator is anyone with superuser power or in "administrators" group.
    """
    model = models.Person
    search_fields = (
        'personal__icontains',
        'family__icontains',
        'email__icontains',
        'username__icontains'
    )

    def get_query(self, request, term):
        results = super().get_query(request, term)
        admin_group = Group.objects.get(name='administrators')
        results = results.filter(
            Q(is_superuser=True) | Q(groups__in=[admin_group])
        ).distinct()
        return results


@lookup_only_for_admins
class AirportLookup(ModelLookup):
    model = models.Airport
    search_fields = (
        'iata__icontains',
        'fullname__icontains'
    )


class LanguageLookup(ModelLookup):
    model = models.Language
    search_fields = (
        'name__icontains',
        'subtag__icontains',
    )

    def get_query(self, request, term):
        # Order the languages by their decreasing popularity
        results = super().get_query(request, term)
        if 'subtag' in request.GET.keys():
            return results.filter(subtag__iexact=term)
        return results.annotate(person_count=Count('person'))\
                .order_by('-person_count')


registry.register(GitHubUserLookup)
registry.register(EventLookup)
registry.register(OrganizationLookup)
registry.register(TTTEventLookup)
registry.register(PersonLookup)
registry.register(AdminLookup)
registry.register(AirportLookup)
registry.register(LanguageLookup)
