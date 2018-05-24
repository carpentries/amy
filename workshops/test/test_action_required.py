from django.urls import reverse

from .base import TestBase
from ..forms import ActionRequiredPrivacyForm
from ..models import Person


class TestActionRequiredPrivacy(TestBase):
    def setUp(self):
        super()._setUpAirports()
        super()._setUpBadges()
        # super()._setUpUsersAndLogin()
        self.neville = Person.objects.create(
            personal='Neville', family='Longbottom',
            email='neville@longbottom.com', gender='M', may_contact=True,
            publish_profile=False, airport=self.airport_0_0,
            username='longbottom_neville',
            data_privacy_agreement=False,
            is_active=True,
        )
        self.neville.save()

    def test_agreement_already_set(self):
        """Make sure the view redirect somewhere if person has already agreed
        to the privacy policy."""
        # force login Neville
        self.client.force_login(self.neville)

        url = reverse('action_required_privacy')

        # form renders
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # Neville decided to agree on the privacy policy for this test
        self.neville.data_privacy_agreement = True
        self.neville.save()

        # form redirects
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 302)

    def test_agreement_submit(self):
        "Make sure the form passes only when `data_agreement_policy` is set."
        # setup sample data
        data = {
            'data_privacy_agreement': False,
            'may_contact': False,
            'publish_profile': False,
        }

        # make sure it doesn't pass without the privacy policy consent
        form = ActionRequiredPrivacyForm(data, instance=self.neville)
        self.assertFalse(form.is_valid())

        # let's try with consent for privacy policy
        data.update({'data_privacy_agreement': True})
        form = ActionRequiredPrivacyForm(data, instance=self.neville)
        self.assertTrue(form.is_valid())
