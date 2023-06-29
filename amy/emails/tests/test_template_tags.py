from django.test import TestCase

from emails.templatetags.emails import is_email_module_enabled


class TestEmailsTemplateTags(TestCase):
    def test_feature_flag_enabled(self) -> None:
        with self.settings(EMAIL_MODULE_ENABLED=False):
            self.assertEqual(is_email_module_enabled(), False)
        with self.settings(EMAIL_MODULE_ENABLED=True):
            self.assertEqual(is_email_module_enabled(), True)
