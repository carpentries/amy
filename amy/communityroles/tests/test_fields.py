from django.core.exceptions import ValidationError

import json
from communityroles.fields import CustomKeysWidget
from workshops.tests.base import TestBase


class TestCustomKeysField(TestBase):
    def setUp(self):
        self.widget = CustomKeysWidget()

    def test_custom_keys_apply_labels(self):
        self.widget.apply_labels(["Test"])
        self.assertEqual(self.widget.labels, ["Test"])

    def test_custom_keys_create_subwidgets(self):
        custom_keys = ["Test", "Second test"]
        values = {"Test": "test value", "Second test": "second test value"}
        self.widget.apply_labels(custom_keys)
        self.assertEqual(self.widget.labels, custom_keys)

        context = self.widget.get_context(
            name="communityroles-custom_keys", value=json.dumps(values), attrs={}
        )

        subwidgets = context["widget"]["subwidgets"]
        subwidget_labels = [w["label"] for w in subwidgets]
        subwidget_values = [w["value"] for w in subwidgets]
        self.assertListEqual(subwidget_labels, custom_keys)
        self.assertListEqual(subwidget_values, list(values.values()))

    def test_custom_keys_none(self):
        self.widget.apply_labels([])
        context = self.widget.get_context(
            name="communityroles-custom_keys", value="null", attrs={}
        )

        self.assertEqual(context["widget"]["subwidgets"], [])
