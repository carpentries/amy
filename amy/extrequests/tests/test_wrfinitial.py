from datetime import date

from django.db.models import Model, Q, QuerySet
from django.test import RequestFactory, TestCase

from extrequests.base_views import AMYCreateAndFetchObjectView
from extrequests.models import SelfOrganisedSubmission, WorkshopInquiryRequest
from extrequests.views import (
    SelfOrganisedSubmissionAcceptEvent,
    WorkshopInquiryAcceptEvent,
    WorkshopRequestAcceptEvent,
)
from workshops.forms import EventCreateForm
from workshops.models import (
    Curriculum,
    Event,
    Language,
    Membership,
    Organization,
    Tag,
    WorkshopRequest,
)


class InitialWRFTestMixin[_T: Model](TestCase):
    view_class: type[AMYCreateAndFetchObjectView[Event, _T, EventCreateForm]]

    def setUpOther(self) -> _T:
        raise NotImplementedError()

    def setUp(self) -> None:
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
            "host": Organization.objects.all()[0],
            "start": date(2020, 11, 11),
            "end": date(2020, 11, 12),
            "membership": None,
        }


class TestInitialWorkshopRequestAccept(InitialWRFTestMixin[WorkshopRequest]):
    view_class = WorkshopRequestAcceptEvent

    def setUp(self) -> None:
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

    def setUpOther(self) -> WorkshopRequest:
        other_object = WorkshopRequest.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution=Organization.objects.all()[0],
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

    def test_get_initial(self) -> None:
        initial = self.view.get_initial()

        self.assertEqual(initial.keys(), self.expected.keys())
        for key in self.expected:
            if isinstance(self.expected[key], QuerySet):
                self.assertEqual(list(initial[key]), list(self.expected[key]))  # type: ignore[call-overload]
            else:
                self.assertEqual(initial[key], self.expected[key])


class TestInitialWorkshopInquiryAccept(InitialWRFTestMixin[WorkshopInquiryRequest]):
    view_class = WorkshopInquiryAcceptEvent

    def setUpOther(self) -> WorkshopInquiryRequest:
        other_object = WorkshopInquiryRequest.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution=Organization.objects.all()[0],
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

    def test_get_initial(self) -> None:
        initial = self.view.get_initial()

        self.assertEqual(initial.keys(), self.expected.keys())
        for key in self.expected:
            if isinstance(self.expected[key], QuerySet):
                self.assertEqual(list(initial[key]), list(self.expected[key]))  # type: ignore[call-overload]
            else:
                self.assertEqual(initial[key], self.expected[key])


class TestInitialSelfOrganisedSubmissionAccept(InitialWRFTestMixin[SelfOrganisedSubmission]):
    view_class = SelfOrganisedSubmissionAcceptEvent

    def setUpOther(self) -> SelfOrganisedSubmission:
        other_object = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution=Organization.objects.all()[0],
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

    def test_get_initial(self) -> None:
        initial = self.view.get_initial()

        self.assertEqual(initial.keys(), self.expected.keys())
        for key in self.expected:
            if isinstance(self.expected[key], QuerySet):
                self.assertEqual(list(initial[key]), list(self.expected[key]))  # type: ignore[call-overload]
            else:
                self.assertEqual(initial[key], self.expected[key])
