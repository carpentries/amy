from unittest.mock import patch

from django.test import RequestFactory, TestCase
from flags.sources import Condition, Flag

from src.workshops.context_processors import feature_flags_enabled


class TestFeatureFlagsEnabled(TestCase):
    def test_context_processor(self) -> None:
        # Arrange
        request = RequestFactory().get("/?test=True")
        condition = Condition(condition="parameter", value="test=True")
        flag = Flag(name="TEST_FLAG", conditions=[condition])
        flags = {"TEST_FLAG": flag}

        mock_get_flags = patch("src.workshops.context_processors.get_flags").start()
        mock_get_flags.return_value = flags

        # Act
        results = feature_flags_enabled(request)

        # Assert
        self.assertEqual(results, {"FEATURE_FLAGS_ENABLED": [flag]})
