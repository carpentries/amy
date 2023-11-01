from unittest.mock import MagicMock, patch
import uuid

from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase
from django.urls import reverse
from flags.sources import Condition, Flag

from workshops.middleware.feature_flags import SaveSessionFeatureFlagMiddleware
from workshops.models import Organization
from workshops.tests.base import TestBase


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


class TestIdempotenceMiddleware(TestBase):
    def setUp(self):
        self._setUpOrganizations()
        self._setUpUsersAndLogin()

    def test_call__get_does_not_check_cache(self):
        """Non-POST requests should not trigger the cache to be created."""
        # Act
        rv = self.client.get(
            reverse("organization_details", args=[self.org_alpha.domain])
        )

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotIn("idempotence_token_cache", self.client.session)

    def test_call__post_no_token(self):
        """POST requests should trigger the cache to be created."""
        # Arrange
        data = {"domain": "example.com", "fullname": "Test Organization"}

        # Act
        rv = self.client.post(reverse("organization_add"), data=data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        print(self.client.session.items())
        # cache should be created, but have no items
        self.assertIn("idempotence_token_cache", self.client.session)
        self.assertEqual(len(self.client.session["idempotence_token_cache"]), 0)

    def test_call__post__once_with_token(self):
        # Arrange
        token = uuid.uuid4()
        data = {
            "domain": "example.com",
            "fullname": "Test Organization",
            "idempotence_token": token,
        }

        # Act
        self.client.post(reverse("organization_add"), data=data, follow=True)

        # Assert
        # cache should be created, and have an entry for our token token
        self.assertIn("idempotence_token_cache", self.client.session)
        self.assertEqual(len(self.client.session["idempotence_token_cache"]), 1)
        self.assertIn(str(token), self.client.session["idempotence_token_cache"])

    @patch("workshops.middleware.idempotence.messages")
    def test_call__post__twice_with_token(self, messages_mock):
        # Arrange
        token = uuid.uuid4()
        data = {
            "domain": "example.com",
            "fullname": "Test Organization",
            "idempotence_token": token,
        }

        # Act
        # submit the same request twice in quick succession
        self.client.post(reverse("organization_add"), data=data, follow=True)
        self.client.post(reverse("organization_add"), data=data, follow=True)

        # Assert
        # cache should be created, and have an entry for our token token
        self.assertIn("idempotence_token_cache", self.client.session)
        self.assertEqual(len(self.client.session["idempotence_token_cache"]), 1)
        self.assertIn(str(token), self.client.session["idempotence_token_cache"])
        # confirm that only one Organization was created
        self.assertEqual(
            Organization.objects.filter(fullname="Test Organization").count(), 1
        )
        self.assertEqual(messages_mock.info.call_count, 1)
        self.assertIn(
            "Found duplicate POST request", messages_mock.info.call_args.args[1]
        )
