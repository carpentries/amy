from django.test import TestCase
from flags.sources import Condition, Flag

from workshops.templatetags.feature_flag_conditions import (
    first_parameter_condition,
    parameter_strip_value,
)


class TestFeatureFlagConditions(TestCase):
    def test_first_parameter_condition(self):
        # Arrange
        condition1 = Condition(condition="session", value="test")
        condition2 = Condition(condition="parameter", value="test")
        condition3 = Condition(condition="boolean", value="test")
        flag = Flag(name="TEST_FLAG", conditions=[condition1, condition2, condition3])
        # Act
        result = first_parameter_condition(flag)
        # Assert
        self.assertEqual(result, condition2)

    def test_first_parameter_condition__not_found(self):
        # Arrange
        condition1 = Condition(condition="session", value="test")
        condition2 = Condition(condition="user", value="test")
        condition3 = Condition(condition="boolean", value="test")
        flag = Flag(name="TEST_FLAG", conditions=[condition1, condition2, condition3])
        # Act
        result = first_parameter_condition(flag)
        # Assert
        self.assertIsNone(result)

    def test_url_parameter_strip_value(self):
        # Arrange
        url = "https://example.com/?test=1asdf"
        # Act
        result = parameter_strip_value(url)
        # Assert
        self.assertEqual(result, "https://example.com/?test")

    def test_url_parameter_strip_value__missing_rhs(self):
        # Arrange
        url = "test"
        # Act
        result = parameter_strip_value(url)
        # Assert
        self.assertEqual(result, "test")
