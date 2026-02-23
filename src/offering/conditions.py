from django.conf import settings
from flags import conditions  # type: ignore[import-untyped]


@conditions.register("not_in_production")  # type: ignore[untyped-decorator]
def not_in_production_condition(value: bool, **kwargs: object) -> bool:
    """Returns True when the app is not running in production (PROD_ENVIRONMENT=False).

    Use as a required flag condition to permanently disable a flag in production:
        {"condition": "not_in_production", "value": True, "required": True}
    """
    return not settings.PROD_ENVIRONMENT
