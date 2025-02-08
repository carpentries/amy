import json

from communityroles.fields import CustomKeysWidget
from workshops.tests.base import TestBase


class TestCustomKeysField(TestBase):
    def setUp(self):
        self.widget = CustomKeysWidget()

    def test_custom_keys_apply_labels(self):
        # Arrange
        custom_keys = ["Test", "Second test"]

        # Act
        self.widget.apply_labels(custom_keys)

        # Assert
        self.assertEqual(self.widget.labels, custom_keys)

    def test_custom_keys_create_subwidgets(self):
        # Arrange
        custom_keys = ["Test", "Second test"]
        values = {"Test": "test value", "Second test": "second test value"}
        self.widget.apply_labels(custom_keys)

        # Act
        context = self.widget.get_context(name="communityroles-custom_keys", value=json.dumps(values), attrs={})
        subwidgets = context["widget"]["subwidgets"]
        subwidget_labels = [w["label"] for w in subwidgets]
        subwidget_values = [w["value"] for w in subwidgets]

        # Assert
        self.assertListEqual(subwidget_labels, custom_keys)
        self.assertListEqual(subwidget_values, list(values.values()))

    def test_custom_keys_value_null(self):
        # Arrange
        custom_keys = ["Test"]
        self.widget.apply_labels(custom_keys)

        # Act
        context = self.widget.get_context(name="communityroles-custom_keys", value="null", attrs={})
        subwidget = context["widget"]["subwidgets"][0]

        # Assert
        self.assertEqual(subwidget["value"], None)

    def test_custom_keys_value_invalid(self):
        # Arrange
        custom_keys = ["Test"]
        # set a value which cannot be parsed as dict - should be ignored
        values = ["Test value"]
        self.widget.apply_labels(custom_keys)

        # Act
        context = self.widget.get_context(name="communityroles-custom_keys", value=json.dumps(values), attrs={})
        subwidget = context["widget"]["subwidgets"][0]

        # Assert
        # subwidget should use the default label as a fallback
        self.assertEqual(subwidget["value"], None)
