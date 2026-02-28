from collections.abc import Sequence
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
    except AttributeError as e:
        raise ValueError("Invalid URI2") from e


# custom URI for links to individual models in API, e.g. "api:person/1234"
ApiUri = Annotated[str, AfterValidator(partial(uri_validator, expected_scheme="api"))]

ValueUri = Annotated[str, AfterValidator(partial(uri_validator, expected_scheme="value"))]


class SinglePropertyLinkModel(BaseModel):
    api_uri: ApiUri
    property: str


class SingleValueLinkModel(BaseModel):
    value_uri: ValueUri


ToHeaderModel = RootModel[Sequence[SinglePropertyLinkModel | SingleValueLinkModel]]

ContextModel = RootModel[dict[str, ApiUri | list[ApiUri] | ValueUri]]
