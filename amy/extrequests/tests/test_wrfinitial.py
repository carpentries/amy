from datetime import date

from django.test import TestCase, RequestFactory
from django.db.models import Q, QuerySet

from extrequests.models import WorkshopInquiryRequest, SelfOrganisedSubmission
from workshops.models import WorkshopRequest, Language, Curriculum, Tag, Organization
from extrequests.views import (
    WorkshopRequestAcceptEvent,
    WorkshopInquiryAcceptEvent,
    SelfOrganisedSubmissionAcceptEvent,
)


class InitialWRFTestMixin:
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.view = self.view_class()
        self.view.setup(self.request)
        self.view.other_object = self.setUpOther()
        self.expected = {
            "public_status": "public",
            "curricula": Curriculum.objects.filter(
                slug__in=[
                    "swc-other",
                    "dc-other",
                    "lc-other",
                    "",  # mix & match
                ]
            ),
            "tags": Tag.objects.filter(
                name__in=[
                    "Circuits",
                    "online",
                ]
            ),
            "contact": "test@example.org;test2@example.org",
            "host": Organization.objects.first(),
            "start": date(2020, 11, 11),
            "end": date(2020, 11, 12),
        }

    def test_get_initial(self):
        initial = self.view.get_initial()

        self.assertEqual(initial.keys(), self.expected.keys())
        for key in self.expected:
            if isinstance(self.expected[key], QuerySet):
                self.assertEqual(list(initial[key]), list(self.expected[key]))
            else:
                self.assertEqual(initial[key], self.expected[key])


class TestInitialWorkshopRequestAccept(InitialWRFTestMixin, TestCase):
    view_class = WorkshopRequestAcceptEvent

    def setUpOther(self):
        other_object = WorkshopRequest.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution=Organization.objects.first(),
            location="Scotland",
            preferred_dates=date(2020, 11, 11),
            language=Language.objects.get(name="English"),
            number_attendees="10-40",
            administrative_fee="nonprofit",
            additional_contact="test@example.org;test2@example.org",
            online_inperson="online",
        )
        # add "(swc|dc|lc)-other" and "mix & match" curricula
        other_object.requested_workshop_types.set(
            Curriculum.objects.filter(
                Q(carpentry__in=["SWC", "DC", "LC"], other=True) | Q(mix_match=True)
            )
        )
        return other_object


class TestInitialWorkshopInquiryAccept(InitialWRFTestMixin, TestCase):
    view_class = WorkshopInquiryAcceptEvent

    def setUpOther(self):
        other_object = WorkshopInquiryRequest.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution=Organization.objects.first(),
            location="Scotland",
            preferred_dates=date(2020, 11, 11),
            language=Language.objects.get(name="English"),
            number_attendees="10-40",
            administrative_fee="nonprofit",
            additional_contact="test@example.org;test2@example.org",
            online_inperson="online",
        )
        # add "(swc|dc|lc)-other" and "mix & match" curricula
        other_object.requested_workshop_types.set(
            Curriculum.objects.filter(
                Q(carpentry__in=["SWC", "DC", "LC"], other=True) | Q(mix_match=True)
            )
        )
        return other_object


class TestInitialSelfOrganisedSubmissionAccept(InitialWRFTestMixin, TestCase):
    view_class = SelfOrganisedSubmissionAcceptEvent

    def setUpOther(self):
        other_object = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution=Organization.objects.first(),
            start=date(2020, 11, 11),
            end=date(2020, 11, 12),
            language=Language.objects.get(name="English"),
            additional_contact="test@example.org;test2@example.org",
            online_inperson="online",
        )
        # add "(swc|dc|lc)-other" and "mix & match" curricula
        other_object.workshop_types.set(
            Curriculum.objects.filter(
                Q(carpentry__in=["SWC", "DC", "LC"], other=True) | Q(mix_match=True)
            )
        )
        return other_object
