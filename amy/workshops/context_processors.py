from pathlib import Path
from typing import cast

from django.conf import settings
from django.http import HttpRequest
from flags.sources import get_flags
import toml


def read_version_from_toml() -> str:
    pyproject_toml_file = Path(__file__).parent.parent.parent / "pyproject.toml"
    data = toml.load(pyproject_toml_file)
    return cast(str, data["project"]["version"])


def version(request: HttpRequest) -> dict:
    version = read_version_from_toml()
    return {"amy_version": version}


def site_banner(request: HttpRequest) -> dict:
    data = {"SITE_BANNER_STYLE": settings.SITE_BANNER_STYLE}
    return data


def feature_flags_enabled(request: HttpRequest) -> dict:
    flags = get_flags(request=request)
    data = {"FEATURE_FLAGS_ENABLED": [flag for flag in flags.values() if flag.check_state(request=request) is True]}
    return data
