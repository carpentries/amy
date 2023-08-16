from unittest.mock import MagicMock, patch

from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase
from flags.sources import Condition, Flag

from workshops.middleware.feature_flags import SaveSessionFeatureFlagMiddleware


class TestSaveSessionFeatureFlagMiddleware(TestCase):
    def test_conditions_of_type(self):
        # Arrange
        condition1 = Condition(condition="session", value="test")
        condition2 = Condition(condition="parameter", value="test")
        condition3 = Condition(condition="boolean", value="test")
        flag = Flag(name="TEST_FLAG", conditions=[condition1, condition2, condition3])
        flags = {"TEST_FLAG": flag}
        # Act
        result = SaveSessionFeatureFlagMiddleware.conditions_of_type(
            flags=flags, type="parameter"
        )
        # Assert
        self.assertEqual(result, [condition2])

    def test_get_parameter_name_from_condition(self):
        # Arrange
        condition = Condition(condition="parameter", value="test=value")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(
            condition
        )
        # Assert
        self.assertEqual(result, "test")

    def test_get_parameter_name_from_condition__missing_rhs(self):
        # Arrange
        condition = Condition(condition="parameter", value="test=")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(
            condition
        )
        # Assert
        self.assertEqual(result, "test")

    def test_get_parameter_name_from_condition__missing_rhs_and_lhs(self):
        # Arrange
        condition = Condition(condition="parameter", value="=")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(
            condition
        )
        # Assert
        self.assertEqual(result, "")

    def test_get_parameter_name_from_condition__missing_lhs(self):
        # Arrange
        condition = Condition(condition="parameter", value="=test")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(
            condition
        )
        # Assert
        self.assertEqual(result, "")

    def test_enable_feature_flag(self):
        # Arrange
        request = MagicMock()
        flag_name = "test"
        # Act
        SaveSessionFeatureFlagMiddleware.enable_feature_flag(request, flag_name)
        # Assert
        request.session.__setitem__.assert_called_once_with(flag_name, True)

    def test_disable_feature_flag(self):
        # Arrange
        request = MagicMock()
        flag_name = "test"
        # Act
        SaveSessionFeatureFlagMiddleware.disable_feature_flag(request, flag_name)
        # Assert
        request.session.__setitem__.assert_called_once_with(flag_name, False)

    def test_call__set_session_variable(self):
        # Arrange
        request = RequestFactory().get("/?test=True")
        session = SessionStore()
        session.save()
        request.session = session

        condition = Condition(condition="parameter", value="test=True")
        flags = {"TEST_FLAG": Flag(name="TEST_FLAG", conditions=[condition])}

        mock_get_flags = patch("workshops.middleware.feature_flags.get_flags").start()
        mock_get_flags.return_value = flags

        middleware = SaveSessionFeatureFlagMiddleware(get_response=lambda x: x)

        # Act
        middleware(request)

        # Assert
        self.assertEqual(request.session.get("test"), True)

    def test_call__unset_session_variable(self):
        # Arrange
        request = RequestFactory().get("/?test=False")
        session = SessionStore()
        session["test"] = True  # needs to be set before running the middleware
        session.save()
        request.session = session

        condition = Condition(condition="parameter", value="test=True")
        flags = {"TEST_FLAG": Flag(name="TEST_FLAG", conditions=[condition])}

        mock_get_flags = patch("workshops.middleware.feature_flags.get_flags").start()
        mock_get_flags.return_value = flags

        middleware = SaveSessionFeatureFlagMiddleware(get_response=lambda x: x)

        # Act
        middleware(request)

        # Assert
        self.assertEqual(request.session.get("test"), False)
