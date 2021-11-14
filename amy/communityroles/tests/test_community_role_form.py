from fiscal.models import Membership
from workshops.models import Award, Person
from workshops.tests.base import TestBase

from ..forms import CommunityRoleForm
from ..models import CommunityRoleConfig


# TODO: figure out why tests fail with:
#  RuntimeError: Model class amy.communityroles.models.CommunityRoleConfig
#  doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS.
class TestCommunityRoleForm(TestBase):
    def test_clean_success(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=None,
            generic_relation_multiple_items=False,
        )
        # TODO: finish
        test_person = Person()
        test_membership = Membership()
        test_award = Award()
        data = {
            "config": test_config.pk,
            "person": test_person.pk,
            "award": test_award.pk,
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": test_membership.pk,
            "url": "https://example.org",
            "generic_relation_m2m": [],
        }
        form = CommunityRoleForm(data)

        # Act & Assert
        form.is_valid()  # should not fail
