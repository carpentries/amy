from datetime import timedelta, date

from django.test import TestCase

from autoemails.actions import SelfOrganisedRequestAction
from autoemails.models import Trigger, EmailTemplate
from extrequests.models import SelfOrganisedSubmission
from workshops.fields import TAG_SEPARATOR
from workshops.models import (
    Event,
    Tag,
    Organization,
    Curriculum,
    Language,
)


class TestSelfOrganisedRequestAction(TestCase):
    def setUp(self):
        # we're missing some tags
        Tag.objects.bulk_create(
            [
                Tag(name="automated-email", priority=0),
                Tag(name="SWC", priority=10),
                Tag(name="DC", priority=20),
                Tag(name="LC", priority=30),
                Tag(name="TTT", priority=40),
            ]
        )
        # by default there's only self-organized organization, but it can't be
        # used in SelfOrganisedRequestAction
        Organization.objects.bulk_create(
            [
                Organization(domain="carpentries.org", fullname="Instructor Training"),
                Organization(
                    domain="librarycarpentry.org", fullname="Library Carpentry"
                ),
            ]
        )

    def testLaunchAt(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        trigger = Trigger(action="test-action", template=EmailTemplate())
        a = SelfOrganisedRequestAction(trigger=trigger)
        self.assertEqual(a.get_launch_at(), timedelta(hours=1))

    def testCheckConditions(self):
        """Make sure `check` works for various input data."""
        # totally fake Event and SelfOrganisedSubmission
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="self-organized"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "Circuits", "automated-email"]))
        r = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=e,
        )
        r.workshop_types.set(Curriculum.objects.filter(carpentry="LC"))

        # 1st case: everything is good
        self.assertEqual(SelfOrganisedRequestAction.check(e), True)

        # 2nd case: event has no start date
        # result: FAIL
        e.start = None
        e.save()
        self.assertEqual(SelfOrganisedRequestAction.check(e), False)

        # bring back the good date
        e.start = date.today() + timedelta(days=7)
        e.save()
        self.assertEqual(SelfOrganisedRequestAction.check(e), True)

        # 3rd case: event is tagged with one (or more) excluding tags
        # result: FAIL
        for tag in ["cancelled", "stalled", "unresponsive"]:
            e.tags.add(Tag.objects.get(name=tag))
            self.assertEqual(SelfOrganisedRequestAction.check(e), False)
            e.tags.remove(Tag.objects.get(name=tag))

        # retest to make sure it's back to normal
        self.assertEqual(SelfOrganisedRequestAction.check(e), True)

        # 4th case: no administrator
        # result: FAIL
        e.administrator = None
        e.save()
        self.assertEqual(SelfOrganisedRequestAction.check(e), False)
        e.administrator = Organization.objects.get(domain="self-organized")
        e.save()

        # retest to make sure it's back to normal
        self.assertEqual(SelfOrganisedRequestAction.check(e), True)

        # 5th case: wrong administrator (Instructor Training)
        # result: FAIL
        e.administrator = Organization.objects.get(domain="carpentries.org")
        e.save()
        self.assertEqual(SelfOrganisedRequestAction.check(e), False)

        # retest to make sure it's back to normal
        e.administrator = Organization.objects.get(domain="self-organized")
        e.save()
        self.assertEqual(SelfOrganisedRequestAction.check(e), True)

        # 6th case: no related SelfOrganisedSubmission
        # result: FAIL
        e.selforganisedsubmission = None
        e.save()
        self.assertEqual(SelfOrganisedRequestAction.check(e), False)

    def testContext(self):
        """Make sure `get_additional_context` works correctly."""
        a = SelfOrganisedRequestAction(
            trigger=Trigger(action="test-action", template=EmailTemplate())
        )

        # method fails when obligatory objects are missing
        with self.assertRaises(KeyError):
            a.get_additional_context(dict())  # missing 'event' and 'request'
        with self.assertRaises(AttributeError):
            # now both objects are present, but the method tries to execute
            # `refresh_from_db` on them
            a.get_additional_context(dict(event="dummy", request="dummy"))

        # totally fake Event and SelfOrganisedSubmission
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="self-organized"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "Circuits", "automated-email"]))
        r = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=e,
            additional_contact=TAG_SEPARATOR.join(["hg@magic.uk", "rw@magic.uk"]),
        )
        r.workshop_types.set(Curriculum.objects.filter(carpentry="LC"))

        ctx = a.get_additional_context(objects=dict(event=e, request=r))
        self.maxDiff = None
        self.assertEqual(
            ctx,
            dict(
                workshop=e,
                request=r,
                workshop_main_type="LC",
                dates=e.human_readable_date,
                host=Organization.objects.first(),
                regional_coordinator_email=["admin-uk@carpentries.org"],
                short_notice=True,
                all_emails=["harry@hogwarts.edu", "hg@magic.uk", "rw@magic.uk"],
                assignee="Regional Coordinator",
                tags=["automated-email", "Circuits", "LC"],
            ),
        )

    def testRecipients(self):
        """Make sure SelfOrganisedRequestAction correctly renders recipients.

        They should get overwritten by SelfOrganisedRequestAction during email
        building."""
        # totally fake Event and SelfOrganisedSubmission
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="self-organized"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "Circuits", "automated-email"]))
        r = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=e,
            additional_contact=TAG_SEPARATOR.join(["hg@magic.uk", "rw@magic.uk"]),
        )
        r.workshop_types.set(Curriculum.objects.filter(carpentry="LC"))

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome to {{ site.name }}",
            to_header="recipient@address.com",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="{{ reply_to }}",
            body_template="Sample text.",
        )
        trigger = Trigger.objects.create(
            action="self-organised-request-form", template=template,
        )
        a = SelfOrganisedRequestAction(
            trigger=trigger, objects=dict(event=e, request=r),
        )
        email = a._email()
        self.assertEqual(email.to, ["harry@hogwarts.edu", "hg@magic.uk", "rw@magic.uk"])

    def test_event_slug(self):
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            venue="Ministry of Magic",
        )
        e.tags.set(Tag.objects.filter(name="LC"))

        a = SelfOrganisedRequestAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e),
        )

        self.assertEqual(a.event_slug(), "test-event")

    def test_all_recipients(self):
        # totally fake Event and SelfOrganisedSubmission
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="self-organized"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "Circuits", "automated-email"]))
        r = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=e,
            additional_contact=TAG_SEPARATOR.join(["hg@magic.uk", "rw@magic.uk"]),
        )
        r.workshop_types.set(Curriculum.objects.filter(carpentry="LC"))

        a = SelfOrganisedRequestAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e, request=r),
        )

        self.assertEqual(
            a.all_recipients(), "harry@hogwarts.edu, hg@magic.uk, rw@magic.uk"
        )

    def test_drop_empty_contacts(self):
        e = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="self-organized"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country="GB",
            contact="test@example.com",  # this won't be picked up
        )
        e.tags.set(Tag.objects.filter(name__in=["LC", "Circuits", "automated-email"]))
        r = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=e,
            additional_contact=TAG_SEPARATOR,
        )
        r.workshop_types.set(Curriculum.objects.filter(carpentry="LC"))

        a = SelfOrganisedRequestAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects=dict(event=e, request=r),
        )

        self.assertEqual(a.all_recipients(), "")
        self.assertEqual(
            a.get_additional_context(dict(event=e, request=r))["all_emails"], []
        )
