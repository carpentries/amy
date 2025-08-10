import json
import logging
from typing import Any

from django import forms
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

logger = logging.getLogger("amy")


class CustomKeysWidget(forms.TextInput):
    template_name = "widgets/custom_keys_widget.html"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.subwidget_form = kwargs.pop("subwidget_form", forms.TextInput)
        super().__init__(*args, **kwargs)

    def apply_labels(self, labels: list[str]) -> None:
        self.labels = labels[:]

    def get_context(self, name: str, value: str, attrs: dict[str, Any] | None) -> dict[str, Any]:
        value_deserialized = json.loads(value)
        try:
            value_deserialized_dict = dict(value_deserialized)
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to load custom key values {value_deserialized} to dict: {e}.")
            logger.debug("Proceeding without custom key values...")
            value_deserialized_dict = {}
        default_values = dict([(label, "") for label in self.labels])
        context_value = default_values | value_deserialized_dict

        context = super().get_context(name, context_value, attrs)
        final_attrs = context["widget"]["attrs"]
        id_ = context["widget"]["attrs"].get("id")

        subwidgets = []
        for index, (label, value) in enumerate(context_value.items()):
            widget_attrs = final_attrs.copy()
            if id_:
                widget_attrs["id"] = "{id_}_{index}".format(id_=id_, index=index)

            widget = self.subwidget_form()
            subwidget_context = widget.get_context(name, value, widget_attrs)["widget"]
            subwidgets.append(subwidget_context | {"label": label})

        context["widget"]["subwidgets"] = subwidgets
        return context

    def value_from_datadict(self, data: QueryDict, files: MultiValueDict, name: str) -> list[tuple[str, str]]:
        """Prepare structure stored in database. The structure is tied to
        `CommunityRole.custom_keys` expected format:
            [
                (label1, value1),
                (label2, value2),
                ...
            ]
        """
        try:
            values = data.getlist(name)
        except AttributeError:
            values = data.get(name, [])
        return json.dumps(list(zip(self.labels, values)))

    def value_omitted_from_data(self, data: QueryDict, files: MultiValueDict, name: str) -> bool:
        return False


class CustomKeysJSONField(forms.JSONField):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("widget", CustomKeysWidget)
        super().__init__(**kwargs)

    def apply_labels(self, labels: list[str]) -> None:
        self.labels = labels[:]
        self.widget.apply_labels(self.labels)
