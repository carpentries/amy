from unittest.mock import patch

from django.test import RequestFactory, TestCase
from flags.sources import Condition, Flag

from dashboard.views import AllFeatureFlags


class TestAllFeatureFlagsView(TestCase):
    def test_context_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")

        condition = Condition(condition="parameter", value="test=True")
        flag = Flag(name="TEST_FLAG", conditions=[condition])
        flags = {"TEST_FLAG": flag}

        mock_get_flags = patch("dashboard.views.get_flags").start()
        mock_get_flags.return_value = flags

        # Act
        context = AllFeatureFlags(request=request).get_context_data()

        # Assert
        self.assertEqual(context.keys(), {"feature_flags", "title", "view"})
        self.assertTrue(context["feature_flags"], [flag])
        self.assertEqual(context["title"], "Feature flags")
