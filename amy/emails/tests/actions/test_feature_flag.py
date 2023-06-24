from django.test import TestCase

from emails.actions import check_feature_flag


class TestCheckFeatureFlag(TestCase):
    def test_check_feature_flag(self) -> None:
        with self.settings(EMAIL_MODULE_ENABLED=False):
            self.assertEqual(check_feature_flag(), False)
        with self.settings(EMAIL_MODULE_ENABLED=True):
            self.assertEqual(check_feature_flag(), True)
