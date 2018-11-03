from functools import lru_cache
from json import JSONDecodeError
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.db.models import Q

from workshops.models import (
    Person,
    Role,
    Organization,
    Sponsorship,
    Task,
)
from workshops.util import create_username


class BaseAPIClient(requests.Session):
    """
    An API client that abstracts away the work of dealing with URLs.
    Usage:
    > client = APIClient(event)
    > list(client) -> returns a list of all objects returned by the API.
    > client[23] -> returns the object with pk=23
    """
    ROOT_ENDPOINT = 'api/'

    @lru_cache(maxsize=None)
    def __new__(cls, event):
        """
        Returns an instance of APIClient.
        Throws NotImplementedError if an API does not exist at the root URL.
        """
        try:
            r = requests.get(urljoin(event.url, cls.ROOT_ENDPOINT))
            r.raise_for_status()
            r.json()
        except (requests.exceptions.HTTPError, JSONDecodeError):
            raise NotImplementedError('Conference site does not support an API')
        return super().__new__(cls)

    def __init__(self, event):
        '''Populate API endpoint and set up basic authentication'''
        super().__init__()
        self.event = event
        self.endpoint = urljoin(event.url, self.ENDPOINT)
        self.auth = (
            settings.PYDATA_USERNAME_SECRET, settings.PYDATA_PASSWORD_SECRET)

    def __iter__(self):
        try:
            r = self.get(self.endpoint)
            r.raise_for_status()
            pydata_objs = r.json()
        except (requests.exceptions.HTTPError, JSONDecodeError) as e:
            raise IOError('Cannot fetch instances from API: {}'.format(str(e)))
        for obj in pydata_objs:
            yield self.parse(obj)

    def __contains__(self, pk):
        try:
            self.get(self.endpoint + str(pk)).raise_for_status()
        except requests.exceptions.HTTPError:
            return False
        else:
            return True

    def __getitem__(self, pk):
        if pk not in self:
            raise KeyError(
                '{} does not exist'.format(self.model._meta.verbose_name)
            )
        obj = self.get(self.endpoint + str(pk)).json()
        return self.parse(obj)


class PersonAPIClient(BaseAPIClient):
    ENDPOINT = 'api/speaker/'
    model = Person

    def parse(self, speaker):
        speaker['name'] = speaker['name'].strip()
        personal = speaker['name'].rsplit(' ', 1)[0]
        family = speaker['name'].rsplit(' ', 1)[-1]
        return Person(
            username=speaker['username'],
            personal=personal,
            family=family,
            email=speaker['email'],
            url=speaker['absolute_url'],
        )


class TaskAPIClient(BaseAPIClient):
    ENDPOINT = 'api/presentation/'
    model = Task

    def parse(self, presentation):
        return Task(
            event=self.event,
            person=Person.objects.get_or_create(
                email=presentation['speaker']['email'],
                defaults={
                    'username': create_username('', presentation['speaker']['username']),
                    'personal': presentation['speaker']['name'].rsplit(' ', 1)[0],
                    'family': presentation['speaker']['name'].rsplit(' ', 1)[-1],
                    'url': presentation['speaker']['absolute_url'],
                }
            )[0],
            role=Role.objects.get(name='presenter'),
            title=presentation['title'],
            url=presentation['absolute_url'],
        )


class SponsorshipAPIClient(BaseAPIClient):
    ENDPOINT = 'api/sponsor/'
    model = Sponsorship

    def parse(self, sponsor):
        domain = urlparse(sponsor['external_url']).netloc
        organization = Organization.objects.filter(
            Q(fullname=sponsor['name']) | Q(domain=domain)
        ).first()
        if not organization:
            organization = Organization.objects.create(
                fullname=sponsor['name'],
                domain=domain,
                notes=sponsor['annotation'],
            )
        return Sponsorship(
            organization=organization,
            event=self.event,
            amount=sponsor['level']['cost'],
            contact=Person.objects.get_or_create(
                email=sponsor['contact_email'],
                defaults={
                    'username': create_username('', sponsor['contact_name']),
                    'personal': sponsor['contact_name'].rsplit(' ', 1)[0],
                    'family': sponsor['contact_name'].rsplit(' ', 1)[-1],
                },
            )[0],
        )
