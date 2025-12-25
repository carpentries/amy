from collections.abc import Callable
from functools import wraps

from django.contrib.auth.decorators import login_required as django_login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.http import HttpResponseBase
from django.http.request import HttpRequest

ViewFunction = Callable[..., HttpResponseBase]


def access_control_decorator(
    decorator: Callable[[ViewFunction], ViewFunction],
) -> Callable[[ViewFunction], ViewFunction]:
    """Every function-based view should be decorated with one of access control
    decorators, even if the view is accessible to everyone, including
    unauthorized users (in that case, use @login_not_required)."""

    @wraps(decorator)
    def decorated_access_control_decorator(view: ViewFunction) -> ViewFunction:
        acl = getattr(view, "_access_control_list", [])
        view = decorator(view)
        view._access_control_list = acl + [decorated_access_control_decorator]  # type: ignore
        return view

    return decorated_access_control_decorator


@access_control_decorator
def admin_required(view: ViewFunction) -> ViewFunction:
    def _test(u: AbstractBaseUser | AnonymousUser) -> bool:
        return bool(u.is_authenticated and getattr(u, "is_admin", False))

    return user_passes_test(_test)(view)


@access_control_decorator
def login_required(view: ViewFunction) -> ViewFunction:
    return django_login_required(view)


@access_control_decorator
def login_not_required(view: ViewFunction) -> ViewFunction:
    # @access_control_decorator adds _access_control_list to `view`,
    # so @login_not_required is *not* no-op.
    return view


class OnlyForAdminsMixin(UserPassesTestMixin):
    request: HttpRequest

    def test_func(self) -> bool:
        return self.request.user.is_authenticated and getattr(self.request.user, "is_admin", False)


class OnlyForAdminsNoRedirectMixin(OnlyForAdminsMixin):
    raise_exception = True


class LoginNotRequiredMixin:
    pass
