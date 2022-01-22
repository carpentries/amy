from django.conf import settings
from django.test import TestCase, override_settings

from recruitment.templatetags.instructorrecruitment import (
    is_instructor_recruitment_enabled,
)


class TestInstructorRecruitmentTemplateTags(TestCase):
    def test_feature_flag_enabled(self) -> None:
        with self.settings(INSTRUCTOR_RECRUITMENT_ENABLED=False):
            self.assertEqual(is_instructor_recruitment_enabled(), False)
        with self.settings(INSTRUCTOR_RECRUITMENT_ENABLED=True):
            self.assertEqual(is_instructor_recruitment_enabled(), True)

    @override_settings()
    def test_feature_flag_removed(self) -> None:
        del settings.INSTRUCTOR_RECRUITMENT_ENABLED

        self.assertEqual(is_instructor_recruitment_enabled(), False)
