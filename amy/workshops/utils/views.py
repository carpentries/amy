from collections import defaultdict
from typing import Optional, Protocol

from django.conf import settings
from django.db import IntegrityError
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from workshops.models import Person


class Assignable(Protocol):
    assigned_to: Optional[Person]

    def save(self): ...


def failed_to_delete(request, object, protected_objects, back=None):
    context = {
        "title": "Failed to delete",
        "back": back or object.get_absolute_url,
        "object": object,
        "refs": defaultdict(list),
    }

    for obj in protected_objects:
        # e.g. for model Award its plural name is 'awards'
        name = str(obj.__class__._meta.verbose_name_plural)
        context["refs"][name].append(obj)

    # this trick enables looping through defaultdict instance
    context["refs"].default_factory = None

    return render(request, "workshops/failed_to_delete.html", context)


def assign(obj: Assignable, /, person: Optional[Person]) -> None:
    """Set obj.assigned_to."""
    try:
        obj.assigned_to = person
        obj.save()
    except IntegrityError:
        raise Http404(f"Unable to assign {person} to {obj}.")


def redirect_with_next_support(request: HttpRequest, *args, **kwargs) -> HttpResponseRedirect:
    """Works in the same way as `redirect` except when there is GET parameter
    named "next". In that case, user is redirected to the URL from that
    parameter. If you have a class-based view, use RedirectSupportMixin that
    does the same."""

    next_url = request.GET.get("next", None)
    if next_url is not None and url_has_allowed_host_and_scheme(next_url, allowed_hosts=settings.ALLOWED_HOSTS):
        return redirect(next_url, permanent=False)
    else:
        return redirect(*args, permanent=False, **kwargs)
