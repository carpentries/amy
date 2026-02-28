from django.test import TestCase
from flags.sources import Condition, Flag  # type: ignore[import-untyped]

from src.workshops.templatetags.feature_flag_conditions import (
    can_change_state,
    first_parameter_condition,
    parameter_strip_value,
)


class TestFeatureFlagConditions(TestCase):
    def test_first_parameter_condition(self) -> None:
        # Arrange
        condition1 = Condition(condition="session", value="test")
        condition2 = Condition(condition="parameter", value="test")
        condition3 = Condition(condition="boolean", value="test")
        flag = Flag(name="TEST_FLAG", conditions=[condition1, condition2, condition3])
        # Act
        result = first_parameter_condition(flag)
        # Assert
        self.assertEqual(result, condition2)

    def test_first_parameter_condition__not_found(self) -> None:
        # Arrange
        condition1 = Condition(condition="session", value="test")
        condition2 = Condition(condition="user", value="test")
        condition3 = Condition(condition="boolean", value="test")
        flag = Flag(name="TEST_FLAG", conditions=[condition1, condition2, condition3])
        # Act
        result = first_parameter_condition(flag)
        # Assert
        self.assertIsNone(result)

    def test_can_change_state(self) -> None:
        # Arrange
        condition1 = Condition(condition="session", value="test")
        condition2 = Condition(condition="parameter", value="test")
        condition3 = Condition(condition="boolean", value=True)
        flag1 = Flag(name="TEST_FLAG1", conditions=[condition1, condition2, condition3])
        flag2 = Flag(name="TEST_FLAG2", conditions=[condition3])
        # Act
        result1 = can_change_state(flag1)
        result2 = can_change_state(flag2)
        # Assert
        self.assertTrue(result1)
        self.assertFalse(result2)

    def test_parameter_strip_value(self) -> None:
        # Arrange
        url = "https://example.com/?test=1asdf"
        # Act
        result = parameter_strip_value(url)
        # Assert
        self.assertEqual(result, "https://example.com/?test")

    def test_parameter_strip_value__missing_rhs(self) -> None:
        # Arrange
        url = "test"
        # Act
        result = parameter_strip_value(url)
        # Assert
        self.assertEqual(result, "test")
