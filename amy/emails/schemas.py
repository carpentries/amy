from functools import partial
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel, RootModel


def uri_validator(uri: str, expected_scheme: str = "https") -> str:
    try:
        result = urlparse(uri)
        if result.scheme == expected_scheme:
            return uri
        raise ValueError("Invalid URI1")
    except AttributeError:
        raise ValueError("Invalid URI2")


ApiUri = Annotated[str, AfterValidator(partial(uri_validator, expected_scheme="api"))]
ValueUri = Annotated[
    str, AfterValidator(partial(uri_validator, expected_scheme="value"))
]


class SinglePropertyLinkModel(BaseModel):
    # custom URI for links to individual models in API, e.g. "api:person/1234"
    api_uri: ApiUri
    property: str


ToHeaderModel = RootModel[list[SinglePropertyLinkModel]]

ContextModel = RootModel[dict[str, ApiUri | list[ApiUri] | ValueUri]]
