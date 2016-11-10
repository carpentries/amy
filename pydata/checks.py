from django.conf import settings
from django.core.checks import register, Error, Tags


@register(Tags.urls)
def check_pydata_urls_included_in_urlpatterns(**kwargs):
    '''Check that `pydata.urls` is included in amy.urls'''
    from amy.urls import urlpatterns
    from workshops import urls as workshops_urls
    from . import urls as pydata_urls

    errors = []
    for url in urlpatterns:
        if hasattr(url, 'urlconf_module') and \
           url.urlconf_module == pydata_urls:
            if url.regex.pattern == r'^workshops/':
                break
    else:
        errors.append(
            Error(
                '`pydata.urls` not included in amy.urls.',
                hint=('Include `pydata.urls` in amy.urls.'),
                id='amy.E001',
            )
        )
    return errors


@register(Tags.urls)
def check_pydata_urls_included_before_workshop_urls(**kwargs):
    '''Check that `pydata.urls` is included before `workshops.urls`'''
    from amy.urls import urlpatterns
    from workshops import urls as workshops_urls
    from . import urls as pydata_urls

    errors = []
    for url in urlpatterns:
        if hasattr(url, 'urlconf_module') and \
           url.urlconf_module in [pydata_urls, workshops_urls]:
            break
    if url.urlconf_module == workshops_urls:
        errors.append(
            Error(
                '`pydata.urls` not included before `workshops.urls`.',
                hint=('Include `pydata.urls` before `workshops_urls`.'),
                id='amy.E002',
            )
        )
    return errors


@register(Tags.templates)
def check_pydata_installed_before_workshops(**kwargs):
    errors = []
    if settings.INSTALLED_APPS.index('pydata') > \
       settings.INSTALLED_APPS.index('workshops'):
        errors.append(
            Error(
                '`pydata` installed after `workshops` app.',
                hint=('Add `pydata` to INSTALLED_APPS before the `workshops` app.'),
                id='amy.E003',
            ),
        )
    return errors


@register(Tags.security)
def check_pydata_username_password_in_settings(**kwargs):
    errors = []
    try:
        if settings.PYDATA_USERNAME_SECRET is None:
            errors.append(
                Error('`PYDATA_USERNAME_SECRET` is undefined in settings.py'),
            )
    except AttributeError:
        errors.append(
            Error('`PYDATA_USERNAME_SECRET` is missing in settings.py'),
        )
    try:
        if settings.PYDATA_PASSWORD_SECRET is None:
            errors.append(
                Error('`PYDATA_PASSWORD_SECRET` is undefined in settings.py'),
            )
    except AttributeError:
        errors.append(
            Error('`PYDATA_PASSWORD_SECRET` is missing in settings.py'),
        )
    return errors
