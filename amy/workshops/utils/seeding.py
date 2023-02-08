from logging import Logger
from typing import Callable, Sequence, Type, TypedDict, cast

from django.db.models import Model


def seed_models(
    model_class: Type[Model],
    model_definition_list: Sequence[TypedDict],
    lookup_field: str,
    model_definition_transformation: Callable[[dict], Model],
    logger: Logger | None = None,
) -> None:
    def _info(msg: str) -> None:
        if logger:
            logger.info(msg)

    class_name = model_class.__name__

    _info(f"Start of {class_name} seeding.")

    for i, model_definition in enumerate(model_definition_list):
        model_id = model_definition[lookup_field]

        if model_class._default_manager.filter(**{lookup_field: model_id}).exists():
            _info(f"{i} {class_name} <{model_id}> already exists, skipping.")
            continue

        _info(f"{i} {class_name} <{model_id}> doesn't exist, creating.")
        _info(f"{i} {class_name} <{model_id}> calling model definition transform.")
        model = model_definition_transformation(cast(dict, model_definition))
        model.save()

    _info(f"End of {class_name} seeding.")


def deprecate_models(
    model_class: Type[Model],
    model_id_list: Sequence[str],
    lookup_field: str,
    logger: Logger | None = None,
) -> None:
    def _info(msg: str) -> None:
        if logger:
            logger.info(msg)

    class_name = model_class.__name__

    _info(f"Start of {class_name} deprecation.")

    for i, model_id in enumerate(model_id_list):
        if not model_class._default_manager.filter(**{lookup_field: model_id}).exists():
            _info(f"{i} {class_name} <{model_id}> doesn't exist, skipping.")
            continue

        _info(f"{i} {class_name} <{model_id}> exists, removing.")
        model_class._default_manager.filter(**{lookup_field: model_id}).delete()

    _info(f"End of {class_name} deprecation.")
