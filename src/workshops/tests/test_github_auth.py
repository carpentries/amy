from unittest.mock import MagicMock, patch

from src.workshops.github_auth import github_username_to_uid
from src.workshops.tests.base import TestBase


class TestGithubUsernameToUid(TestBase):
    @patch("src.workshops.github_auth.Github.get_user")
    def test_regression_1141(self, get_user_mock: MagicMock) -> None:
        """
        Github.get_user(username) is buggy and raises ConnectionResetError when
        username contains spaces. Test that this case is handled correctly.
        """

        get_user_mock.side_effect = ConnectionResetError

        with self.assertRaises(ValueError):
            github_username_to_uid("asdf qwer")
