import requests

from django.views.generic import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from . import utils


class ConferenceImport(LoginRequiredMixin, View):
    """
    Fetch conference details from `/api/` API endpoint of a
    PyData conference.
    """

    def get(self, request):
        try:
            url = request.GET['url'].rstrip('/')
            conf = requests.get('{}/api'.format(url)).json()
            event = utils.parse_event(conf)
            return JsonResponse(event)
        except requests.exceptions.HTTPError as e:
            return HttpResponseBadRequest(
                'Request for "{0}" returned status code {1}.'
                .format(url, e.response.status_code)
            )
        except requests.exceptions.RequestException:
            return HttpResponseBadRequest('Network connection error.')
        except KeyError:
            return HttpResponseBadRequest('Missing or wrong "url" parameter.')
