from datetime import date

from django.db.models import Q, QuerySet
from django.test import RequestFactory, TestCase

from extrequests.models import SelfOrganisedSubmission, WorkshopInquiryRequest
from extrequests.views import (
    SelfOrganisedSubmissionAcceptEvent,
    WorkshopInquiryAcceptEvent,
    WorkshopRequestAcceptEvent,
)
from workshops.models import (
    Curriculum,
    Language,
    Membership,
    Organization,
    Tag,
    WorkshopRequest,
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
            "membership": None,
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

    def setUp(self):
        self.member_code = "hogwarts55"
        membership = Membership.objects.create(
            name="Hogwarts",
            variant="bronze",
            agreement_start=date(2020, 1, 1),
            agreement_end=date(2021, 1, 1),
            contribution_type="financial",
            registration_code=self.member_code,
        )
        super().setUp()
        self.expected.update({"membership": membership})

    def setUpOther(self):
        other_object = WorkshopRequest.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution=Organization.objects.first(),
            member_code=self.member_code,
            location="Scotland",
            preferred_dates=date(2020, 11, 11),
            language=Language.objects.get(name="English"),
            administrative_fee="nonprofit",
            additional_contact="test@example.org;test2@example.org",
            online_inperson="online",
        )
        # add "(swc|dc|lc)-other" and "mix & match" curricula
        other_object.requested_workshop_types.set(
            Curriculum.objects.filter(Q(carpentry__in=["SWC", "DC", "LC"], other=True) | Q(mix_match=True))
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
            administrative_fee="nonprofit",
            additional_contact="test@example.org;test2@example.org",
            online_inperson="online",
        )
        # add "(swc|dc|lc)-other" and "mix & match" curricula
        other_object.requested_workshop_types.set(
            Curriculum.objects.filter(Q(carpentry__in=["SWC", "DC", "LC"], other=True) | Q(mix_match=True))
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
            Curriculum.objects.filter(Q(carpentry__in=["SWC", "DC", "LC"], other=True) | Q(mix_match=True))
        )
        return other_object
