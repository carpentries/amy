from functools import wraps

from django.contrib.auth.decorators import login_required as django_login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http.request import HttpRequest

from workshops.models import Person


def access_control_decorator(decorator):
    """Every function-based view should be decorated with one of access control
    decorators, even if the view is accessible to everyone, including
    unauthorized users (in that case, use @login_not_required)."""

    @wraps(decorator)
    def decorated_access_control_decorator(view):
        acl = getattr(view, "_access_control_list", [])
        view = decorator(view)
        view._access_control_list = acl + [decorated_access_control_decorator]
        return view

    return decorated_access_control_decorator


@access_control_decorator
def admin_required(view):
    def _test(u: Person) -> bool:
        return u.is_authenticated and u.is_admin

    return user_passes_test(_test)(view)  # type: ignore


@access_control_decorator
def login_required(view):
    return django_login_required(view)


@access_control_decorator
def login_not_required(view):
    # @access_control_decorator adds _access_control_list to `view`,
    # so @login_not_required is *not* no-op.
    return view


class OnlyForAdminsMixin(UserPassesTestMixin):
    request: HttpRequest

    def test_func(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.is_admin  # type: ignore
        )


class OnlyForAdminsNoRedirectMixin(OnlyForAdminsMixin):
    raise_exception = True


class LoginNotRequiredMixin(object):
    pass
