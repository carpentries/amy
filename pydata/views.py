import requests
from urllib.parse import urlparse

from django.views.generic import View
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.exceptions import ValidationError

from workshops.models import (
    Event,
    Person,
    Role,
    Organization,
    Sponsorship,
    Task,
)
from workshops.util import OnlyForAdminsMixin


class BaseImport(OnlyForAdminsMixin, View):
    """
    Fetch an API endpoint at a PyData conference site.
    Returns a JSON response consisting of fields and their values.
    """

    def get_endpoint(self, url):
        """
        Obtain the API endpoint from the import URL.
        """
        raise NotImplementedError('Subclasses should implement this method')

    @classmethod
    def parse(cls, pydata_obj):
        """
        Creates a mapping from an instance of the object from a PyData
        conference to an instance within the AMY database.
        """
        raise NotImplementedError('Subclasses should implement this method')

    def get(self, request):
        try:
            self.url = request.GET['url'].rstrip('/')
            r = requests.get(self.get_endpoint())
            r.raise_for_status()
            pydata_obj = r.json()
            amy_obj = self.parse(pydata_obj)
            return JsonResponse(amy_obj)
        except KeyError:
            return HttpResponseBadRequest('Missing "url" parameter')
        except ValidationError:
            return HttpResponseBadRequest('Invalid "url" parameter')
        except requests.exceptions.HTTPError as e:
            return HttpResponseBadRequest(
                'Request for "{0}" returned status code {1}.'
                .format(self.url, e.response.status_code)
            )
        except requests.exceptions.RequestException:
            return HttpResponseBadRequest('Network connection error.')
        except Exception as e:
            return HttpResponseBadRequest(str(e))


class ConferenceImport(BaseImport):
    """
    Fetch conference details from `/api/` API endpoint of a
    PyData conference.
    """

    @classmethod
    def parse(cls, conf):
        return {
            'slug': '{}-{}'.format(conf['start_date'], conf['title']),
            'start': conf['start_date'],
            'end': conf['end_date'],
        }

    def get_endpoint(self):
        return '{}/api/'.format(self.url)


class PersonImport(BaseImport):
    """
    Fetches details about a speaker from the `/api/speaker/<id>`
    API endpoint of a PyData conference.
    """

    @classmethod
    def parse(cls, speaker):
        personal = speaker['name'].rsplit(' ', 1)[0]
        family = speaker['name'].rsplit(' ', 1)[-1]
        return {
            'personal': personal,
            'family': family,
            'email': speaker['email'],
            'url': speaker['absolute_url'],
        }

    def get_endpoint(self):
        match = Person.PROFILE_REGEX.match(self.url)
        # if not match:
        #     raise ValidationError('Invalid speaker URL', code='invalid')
        conf_url, id = match.groups()
        return '{0}/api/speaker/{1}/'.format(conf_url, id)



class TaskImport(BaseImport):
    """
    Fetches details about a presentation from the `/api/presentation/<id>`
    API endpoint of a PyData conference.
    """

    def parse(self, presentation):
        return {
            'person': presentation['speaker']['email'],
            'role': Role.objects.get(name='presenter').pk,
            'title': presentation['title'],
        }

    def get_endpoint(self):
        match = Task.PRESENTATION_REGEX.match(self.url)
        if not match:
            raise ValidationError('Invalid task URL', code='invalid')
        conf_url, id = match.groups()
        return '{0}/api/presentation/{1}/'.format(conf_url, id)


class SponsorImport(BaseImport):
    """
    Fetches details about a sponsor from the `/api/sponsor/<id>`
    API endpoint of a PyData conference.
    """

    def parse(self, presentation):
        conf_url = Sponsorship.PROFILE_REGEX.match(self.url).group('url')
        domain = urlparse(self.url).netloc
        try:
            org = Organization.objects.get(domain=domain)
            org.fullname = presentation['name']
            org.notes = presentation['annotation']
            org.save()
        except Organization.DoesNotExist:
            org = Organization.objects.create(
                domain=domain,
                fullname=presentation['name'],
                notes=presentation['annotation'],
            )
        return {
            'organization': org.domain,
        }

    def get_endpoint(self):
        match = Sponsorship.PROFILE_REGEX.match(self.url)
        if not match:
            raise ValidationError('Invalid task URL', code='invalid')
        conf_url, id = match.groups()
        return '{0}/api/sponsor/{1}/'.format(conf_url, id)
