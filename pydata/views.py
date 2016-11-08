from json import JSONDecodeError
from urllib.parse import urljoin

import requests
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect, get_object_or_404
from django.template.defaultfilters import slugify
from django.views.generic import View

from workshops.forms import EventLookupForm
from workshops.models import (
    Event,
    Person,
    Sponsorship,
    Task,
)
from workshops.util import OnlyForAdminsMixin
from workshops.base_views import AMYCreateView, AMYFormView

from .api import PersonAPIClient, TaskAPIClient, SponsorshipAPIClient
from .forms import PersonAddFormSet, TaskAddFormSet, SponsorshipAddFormSet


class ConferenceImport(OnlyForAdminsMixin, View):
    """
    Fetch conference details from `/api/` API endpoint of a PyData conference.
    """
    def get(self, request):
        try:
            url = request.GET['url']
            conf = requests.get(urljoin(url, 'api/')).json()
            return JsonResponse({
                'slug': slugify('{}-{}'.format(conf['start_date'], conf['title'])),
                'start': conf['start_date'],
                'end': conf['end_date'],
            })
        except KeyError:
            return HttpResponseBadRequest('Missing "url" parameter')
        except (requests.exceptions.RequestException, JSONDecodeError):
            return HttpResponseBadRequest('Conference site does not support an API')
        except Exception as e:
            return HttpResponseBadRequest(str(e))


class BaseImport(OnlyForAdminsMixin, View):
    """
    Fetch an API endpoint at a PyData conference site.
    Returns a JSON response consisting of fields and their values.
    """

    def serialize(self, obj):
        '''Returns a dict with serializable fields from a model instance'''
        raise NotImplementedError()

    def get_pk(self, url):
        """
        Returns a 2-tuple containing the conference site URL
        and the primary key of the object if the URL is valid.
        Returns None when the URL is invalid.
        """
        raise NotImplementedError()

    def get(self, request):
        try:
            url = request.GET['url']
            conf_url, pk = self.get_pk(url).groups()
            event = Event.objects.get(url__contains=conf_url)
            client = self.client(event)
            obj = client[pk]
            return JsonResponse(self.serialize(obj))
        except KeyError:
            return HttpResponseBadRequest('Missing "url" parameter')
        except AttributeError:
            return HttpResponseBadRequest('Invalid "url" parameter')
        except Event.DoesNotExist:
            return HttpResponseBadRequest('Object does not belong to any event')
        except requests.exceptions.HTTPError as e:
            return HttpResponseBadRequest(
                'Request for "{0}" returned status code {1}.'
                .format(self.url, e.response.status_code)
            )
        except requests.exceptions.RequestException:
            return HttpResponseBadRequest('Network connection error')
        except Exception as e:
            return HttpResponseBadRequest(str(e))


class PersonImport(BaseImport):
    """
    Fetches details about a speaker from the `/api/speaker/<id>`
    API endpoint of a PyData conference.
    """
    client = PersonAPIClient

    def serialize(self, person):
        return {
            'username': person.username,
            'personal': person.personal,
            'family': person.family,
            'email': person.email,
            'url': person.url,
        }

    def get_pk(self, url):
        return Person.PROFILE_REGEX.match(url)


class TaskImport(BaseImport):
    """
    Fetches details about a presentation from the `/api/presentation/<id>`
    API endpoint of a PyData conference.
    """
    client = TaskAPIClient

    def serialize(self, task):
        return {
            'person': task.person.email,
            'role': task.role.pk,
            'title': task.title,
            'url': task.url,
        }

    def get_pk(self, url):
        return Task.PRESENTATION_REGEX.match(url)


class SponsorshipImport(BaseImport):
    """
    Fetches details about a sponsor from the `/api/sponsor/<id>`
    API endpoint of a PyData conference.
    """
    client = SponsorshipAPIClient

    def serialize(self, sponsorship):
        return {
            'organization': sponsorship.organization.domain,
            'amount': sponsorship.amount,
            'contact': sponsorship.contact.email,
        }

    def get_pk(self, url):
        return Sponsorship.PROFILE_REGEX.match(url)


class BulkImportEventSelect(OnlyForAdminsMixin, AMYFormView):
    form_class = EventLookupForm
    template_name = 'workshops/generic_form.html'
    title = 'Bulk import a Conference'

    def form_valid(self, form):
        return redirect(
            reverse(
                'bulk_import_person',
                kwargs={'slug': form.cleaned_data['event'].slug},
            ),
        )


class BaseBulkImport(OnlyForAdminsMixin, AMYCreateView):
    """
    Class-based view for importing instances from PyData API client.
    Overrides AMYCreateView to populate initial data and a custom
    success message.
    """
    success_message = 'Successfully imported {count} {model}'

    def get_initial(self):
        '''Obtain model instances from the API client'''
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        client = self.client(event=event)
        return [model_to_dict(obj) for obj in client]

    def get_form_kwargs(self):
        # Magic:
        # 1. Formset can only be bound when initialized as
        #    `formset = form_class(data=request.POST)`
        # 2. SingleObjectMixin introduces `instances` in kwargs
        #    which is not accepted by the form_class.
        kwargs = super().get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            return {'data': self.request.POST}
        kwargs.pop('instance')
        return kwargs

    def get(self, *args, **kwargs):
        '''Return HTTP400 when API does not respond'''
        try:
            return super().get(*args, **kwargs)
        except (IOError, NotImplementedError) as e:
            return HttpResponseBadRequest(str(e))

    def get_success_message(self, cleaned_data):
        return self.success_message.format(
            count=sum([not data['DELETE'] for data in cleaned_data]),
            model=self.model._meta.verbose_name_plural
        )


class PersonBulkImport(BaseBulkImport):
    model = Person
    form_class = PersonAddFormSet
    client = PersonAPIClient
    template_name = 'pydata/bulk-import/person.html'

    def get_success_url(self):
        return reverse('bulk_import_task', kwargs={'slug': self.kwargs['slug']})


class TaskBulkImport(BaseBulkImport):
    model = Task
    form_class = TaskAddFormSet
    client = TaskAPIClient
    template_name = 'pydata/bulk-import/task.html'

    def get_success_url(self):
        return reverse('bulk_import_sponsorship', kwargs={'slug': self.kwargs['slug']})


class SponsorshipBulkImport(BaseBulkImport):
    model = Sponsorship
    form_class = SponsorshipAddFormSet
    client = SponsorshipAPIClient
    template_name = 'pydata/bulk-import/sponsorship.html'

    def get_success_url(self):
        return reverse('event_details', kwargs={'slug': self.kwargs['slug']})
