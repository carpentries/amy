from django.apps import apps as camelot_apps
from django.core.checks import register, Error, Tags

from amy.urls import urlpatterns
from workshops import urls as workshops_urls

from . import urls as pydata_urls


@register(Tags.urls)
def check_pydata_urls_included_in_urlpatterns(**kwargs):
    '''Check that `pydata.urls` is included in amy.urls'''
    errors = []
    for url in urlpatterns:
        if hasattr(url, 'urlconf_module') and \
           url.urlconf_module == pydata_urls:
            if url.regex.pattern == r'^workshops/':
                break
    else:
        errors.append(
            Error(
                "`pydata.urls` not included in amy.urls.",
                hint=("Include `pydata.urls` in amy.urls."),
                id='amy.E001',
            )
        )
    return errors


@register(Tags.urls)
def check_pydata_urls_included_before_workshop_urls(**kwargs):
    '''Check that `pydata.urls` is included before `workshops.urls`'''
    errors = []
    for url in urlpatterns:
        if hasattr(url, 'urlconf_module') and \
           url.urlconf_module in [pydata_urls, workshops_urls]:
            break
    if url.urlconf_module == workshops_urls:
        errors.append(
            Error(
                "`pydata.urls` not included before `workshops.urls`.",
                hint=("Include `pydata.urls` before `workshops_urls`."),
                id='amy.E002',
            )
        )
    return errors
