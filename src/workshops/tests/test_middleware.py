from unittest.mock import MagicMock, patch

from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils.http import urlencode
from flags.sources import Condition, Flag  # type: ignore[import-untyped]

from src.consents.models import Consent, Term, TermOption, TermOptionChoices
from src.workshops.middleware.feature_flags import SaveSessionFeatureFlagMiddleware
from src.workshops.models import Person
from src.workshops.tests.base import consent_to_all_required_consents


class TestSaveSessionFeatureFlagMiddleware(TestCase):
    def test_conditions_of_type(self) -> None:
        # Arrange
        condition1 = Condition(condition="session", value="test")
        condition2 = Condition(condition="parameter", value="test")
        condition3 = Condition(condition="boolean", value="test")
        flag = Flag(name="TEST_FLAG", conditions=[condition1, condition2, condition3])
        flags = {"TEST_FLAG": flag}
        # Act
        result = SaveSessionFeatureFlagMiddleware.conditions_of_type(flags=flags, type="parameter")
        # Assert
        self.assertEqual(result, [condition2])

    def test_get_parameter_name_from_condition(self) -> None:
        # Arrange
        condition = Condition(condition="parameter", value="test=value")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(condition)
        # Assert
        self.assertEqual(result, "test")

    def test_get_parameter_name_from_condition__missing_rhs(self) -> None:
        # Arrange
        condition = Condition(condition="parameter", value="test=")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(condition)
        # Assert
        self.assertEqual(result, "test")

    def test_get_parameter_name_from_condition__missing_rhs_and_lhs(self) -> None:
        # Arrange
        condition = Condition(condition="parameter", value="=")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(condition)
        # Assert
        self.assertEqual(result, "")

    def test_get_parameter_name_from_condition__missing_lhs(self) -> None:
        # Arrange
        condition = Condition(condition="parameter", value="=test")
        # Act
        result = SaveSessionFeatureFlagMiddleware.get_parameter_name_from_condition(condition)
        # Assert
        self.assertEqual(result, "")

    def test_enable_feature_flag(self) -> None:
        # Arrange
        request = MagicMock()
        flag_name = "test"
        # Act
        SaveSessionFeatureFlagMiddleware.enable_feature_flag(request, flag_name)
        # Assert
        request.session.__setitem__.assert_called_once_with(flag_name, True)

    def test_disable_feature_flag(self) -> None:
        # Arrange
        request = MagicMock()
        flag_name = "test"
        # Act
        SaveSessionFeatureFlagMiddleware.disable_feature_flag(request, flag_name)
        # Assert
        request.session.__setitem__.assert_called_once_with(flag_name, False)

    def test_call__set_session_variable(self) -> None:
        # Arrange
        request = RequestFactory().get("/?test=True")
        session = SessionStore()
        session.save()
        request.session = session

        condition = Condition(condition="parameter", value="test=True")
        flags = {"TEST_FLAG": Flag(name="TEST_FLAG", conditions=[condition])}

        mock_get_flags = patch("src.workshops.middleware.feature_flags.get_flags").start()
        mock_get_flags.return_value = flags

        middleware = SaveSessionFeatureFlagMiddleware(get_response=lambda x: HttpResponse())

        # Act
        middleware(request)

        # Assert
        self.assertEqual(request.session.get("test"), True)

    def test_call__unset_session_variable(self) -> None:
        # Arrange
        request = RequestFactory().get("/?test=False")
        session = SessionStore()
        session["test"] = True  # needs to be set before running the middleware
        session.save()
        request.session = session

        condition = Condition(condition="parameter", value="test=True")
        flags = {"TEST_FLAG": Flag(name="TEST_FLAG", conditions=[condition])}

        mock_get_flags = patch("src.workshops.middleware.feature_flags.get_flags").start()
        mock_get_flags.return_value = flags

        middleware = SaveSessionFeatureFlagMiddleware(get_response=lambda x: HttpResponse())

        # Act
        middleware(request)

        # Assert
        self.assertEqual(request.session.get("test"), False)


class TestForcePasswordChangeMiddleware(TestCase):
    def setUp(self) -> None:
        # Don't rely on required terms added by migrations, they may be missing from the test DB.
        term = Term.objects.create(
            content="I'm a required term",
            slug="required-test-term",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        TermOption.objects.create(term=term, option_type=TermOptionChoices.AGREE)
        self.person = Person.objects.create_user(
            username="user",
            personal="Typical",
            family="User",
            email="user@example.org",
            password="user",
        )
        consent_to_all_required_consents(self.person)
        self.password_url = reverse("person_password", args=[self.person.pk])
        self.dashboard_url = reverse("user-dashboard")

    def force_password_change(self) -> None:
        self.person.force_password_change_on_login = True
        self.person.save()

    def test_anonymous_user_not_redirected(self) -> None:
        # Act
        rv = self.client.get(reverse("login"))
        # Assert
        self.assertEqual(rv.status_code, 200)

    def test_user_without_flag_not_redirected(self) -> None:
        # Arrange
        self.client.force_login(self.person)
        # Act
        rv = self.client.get(self.dashboard_url)
        # Assert
        self.assertEqual(rv.status_code, 200)

    def test_user_with_flag_redirected_to_password_change(self) -> None:
        # Arrange
        self.force_password_change()
        self.client.force_login(self.person)
        # Act
        rv = self.client.get(self.dashboard_url)
        # Assert
        self.assertRedirects(
            rv,
            f"{self.password_url}?{urlencode({'next': self.dashboard_url})}",
            fetch_redirect_response=False,
        )

    def test_password_change_page_accessible(self) -> None:
        # Arrange
        self.force_password_change()
        self.client.force_login(self.person)
        # Act
        rv = self.client.get(self.password_url)
        # Assert
        self.assertEqual(rv.status_code, 200)

    def test_password_change_page_with_next_accessible(self) -> None:
        # Arrange
        self.force_password_change()
        self.client.force_login(self.person)
        # Act
        rv = self.client.get(f"{self.password_url}?{urlencode({'next': self.dashboard_url})}")
        # Assert
        self.assertEqual(rv.status_code, 200)

    def test_next_param_preserved(self) -> None:
        # Arrange
        self.force_password_change()
        self.client.force_login(self.person)
        terms_url = reverse("action_required_terms")
        # Act
        rv = self.client.get(f"{reverse('autoupdate_profile')}?{urlencode({'next': self.dashboard_url})}")
        # Assert
        self.assertRedirects(
            rv,
            f"{self.password_url}?{urlencode({'next': self.dashboard_url})}",
            fetch_redirect_response=False,
        )
        self.assertNotIn(terms_url, rv["Location"])

    def test_other_users_password_page_not_allowed(self) -> None:
        # Arrange
        other = Person.objects.create_user(
            username="other", personal="Other", family="User", email="other@example.org", password="other"
        )
        self.force_password_change()
        self.client.force_login(self.person)
        url = reverse("person_password", args=[other.pk])
        # Act
        rv = self.client.get(url)
        # Assert
        self.assertRedirects(rv, f"{self.password_url}?{urlencode({'next': url})}", fetch_redirect_response=False)

    def test_logout_allowed(self) -> None:
        # Arrange
        self.force_password_change()
        self.client.force_login(self.person)
        # Act
        rv = self.client.post(reverse("logout"))
        # Assert
        self.assertRedirects(rv, reverse("login"), fetch_redirect_response=False)

    def test_terms_page_allowed(self) -> None:
        # Arrange
        self.force_password_change()
        Consent.archive_all_for_person(self.person)
        self.client.force_login(self.person)
        # Act
        rv = self.client.get(reverse("action_required_terms"))
        # Assert
        self.assertEqual(rv.status_code, 200)

    def test_no_redirect_loop_with_terms_middleware(self) -> None:
        """User who must both change password and consent to terms should
        end up on a page that renders, not bounce between redirects."""
        # Arrange
        self.force_password_change()
        Consent.archive_all_for_person(self.person)
        self.client.force_login(self.person)
        # Act
        rv = self.client.get(self.dashboard_url, follow=True)
        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.request["PATH_INFO"], reverse("action_required_terms"))

    def test_flag_cleared_after_password_change(self) -> None:
        # Arrange
        self.force_password_change()
        self.client.force_login(self.person)
        data = {
            "old_password": "user",
            "new_password1": "a-new-Secure-pa55word",
            "new_password2": "a-new-Secure-pa55word",
        }
        # Act
        rv = self.client.post(f"{self.password_url}?{urlencode({'next': self.dashboard_url})}", data)
        # Assert
        self.assertRedirects(rv, self.dashboard_url, fetch_redirect_response=False)
        self.person.refresh_from_db()
        self.assertFalse(self.person.force_password_change_on_login)
        self.assertEqual(self.client.get(self.dashboard_url).status_code, 200)
