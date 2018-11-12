from unittest.mock import patch

from workshops.tests.base import TestBase
from workshops.github_auth import github_username_to_uid


class TestGithubUsernameToUid(TestBase):
    @patch('workshops.github_auth.Github.get_user')
    def test_regression_1141(self, get_user_mock):
        """
        Github.get_user(username) is buggy and raises ConnectionResetError when
        username contains spaces. Test that this case is handled correctly.
        """

        get_user_mock.side_effect = ConnectionResetError

        with self.assertRaises(ValueError):
            got = github_username_to_uid('asdf qwer')
