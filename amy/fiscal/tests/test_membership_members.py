from django.db import IntegrityError
from django.urls import reverse

from fiscal.forms import MemberForm
from workshops.models import Member, MemberRole, Membership
from workshops.tests.base import TestBase


class MembershipTestMixin:
    def setUpMembership(self, consortium: bool):
        self.membership = Membership.objects.create(
            name="Test Membership",
            consortium=consortium,
            public_status="public",
            variant="partner",
            agreement_start="2021-02-14",
            agreement_end="2022-02-14",
            contribution_type="financial",
            public_instructor_training_seats=0,
            additional_public_instructor_training_seats=0,
        )
        self.member_role = MemberRole.objects.first()


class TestMemberFormLayout(TestBase):
    def test_main_helper_layout(self):
        form = MemberForm()

        self.assertEqual(
            list(form.helper.layout),
            ["membership", "organization", "role", "EDITABLE", "id", "DELETE"],
        )

    def test_empty_helper_layout(self):
        form = MemberForm()

        self.assertEqual(len(form.helper_empty_form.layout), 5)
        self.assertEqual(
            list(form.helper_empty_form.layout)[:-1],
            ["membership", "organization", "role", "id"],
        )
        self.assertEqual(form.helper_empty_form.layout[-1].fields, ["DELETE"])


class TestMembershipMembers(MembershipTestMixin, TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_adding_new_member_to_nonconsortium(self):
        """Ensure only 1 member can be added to non-consortium membership."""
        self.setUpMembership(consortium=False)
        self.assertEqual(self.membership.member_set.count(), 0)

        # only 1 member allowed
        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": self.membership.pk,
            "form-0-organization": self.org_alpha.pk,
            "form-0-role": self.member_role.pk,
            "form-0-id": "",
            "form-0-EDITABLE": True,
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )
        self.assertEqual(self.membership.member_set.count(), 1)
        self.assertEqual(list(self.membership.organizations.all()), [self.org_alpha])

        # posting this will fail because only 1 form in the formset is allowed
        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": "",
            "form-0-organization": self.org_alpha.pk,
            "form-0-role": self.member_role.pk,
            "form-0-id": "",
            "form-0-EDITABLE": True,
            "form-1-membership": "",
            "form-1-organization": self.org_beta.pk,
            "form-1-role": self.member_role.pk,
            "form-1-id": "",
            "form-1-EDITABLE": True,
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.membership.member_set.count(), 1)  # number didn't change

    def test_adding_new_members_to_consortium(self):
        """Ensure 1+ members can be added to consortium membership."""
        self.setUpMembership(consortium=True)
        self.assertEqual(self.membership.member_set.count(), 0)
        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": self.membership.pk,
            "form-0-organization": self.org_alpha.pk,
            "form-0-role": self.member_role.pk,
            "form-0-id": "",
            "form-0-EDITABLE": True,
            "form-1-membership": self.membership.pk,
            "form-1-organization": self.org_beta.pk,
            "form-1-role": self.member_role.pk,
            "form-1-id": "",
            "form-1-EDITABLE": True,
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )
        self.assertEqual(self.membership.member_set.count(), 2)
        self.assertEqual(
            list(self.membership.organizations.all()), [self.org_alpha, self.org_beta]
        )

    def test_removing_members_from_nonconsortium(self):
        """Ensure removing the only member from non-consortium membership is not
        allowed."""
        self.setUpMembership(consortium=False)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": "",
            "form-0-organization": m1.organization.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
            "form-0-EDITABLE": True,
            "form-0-DELETE": "on",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)  # response failed
        self.assertEqual(list(self.membership.organizations.all()), [self.org_alpha])

    def test_removing_members_from_consortium(self):
        """Ensure removing all members from consortium membership is allowed."""
        self.setUpMembership(consortium=True)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )
        m2 = Member.objects.create(
            organization=self.org_beta,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 2,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": "",
            "form-0-organization": m1.organization.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
            "form-0-EDITABLE": True,
            "form-0-DELETE": "on",
            "form-1-membership": "",
            "form-1-organization": m2.organization.pk,
            "form-1-role": m2.role.pk,
            "form-1-id": m2.pk,
            "form-1-EDITABLE": True,
            "form-1-DELETE": "on",
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )
        self.assertEqual(list(self.membership.organizations.all()), [])

    def test_mix_adding_removing_members_from_consortium(self):
        """Ensure a mixed-content formset for consortium membership members works
        fine (e.g. a new member is added, and an old one is removed)."""
        self.setUpMembership(consortium=True)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": self.membership.pk,
            "form-0-organization": m1.organization.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
            "form-0-EDITABLE": True,
            "form-0-DELETE": "on",
            "form-1-membership": self.membership.pk,
            "form-1-organization": self.org_beta.pk,
            "form-1-role": self.member_role.pk,
            "form-1-id": "",
            "form-1-EDITABLE": True,
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )

        self.assertEqual(list(self.membership.organizations.all()), [self.org_beta])

    def test_editing_noneditable_members_fails(self):
        """Ensure an attempt to edit member without 'editable' checkbox ticked off
        fails with validation error."""
        self.setUpMembership(consortium=True)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": self.membership.pk,
            "form-0-organization": self.org_beta.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)  # form failed
        self.assertEqual(
            response.context["formset"].errors[0],
            {"__all__": ["Form values weren't supposed to be changed."]},
        )
        self.assertEqual(list(self.membership.organizations.all()), [self.org_alpha])

    def test_not_editing_noneditable_members_succeeds(self):
        """Ensure saving edit member without 'editable' checkbox ticked off works fine.
        No changes are introduced to the member."""
        self.setUpMembership(consortium=True)
        m1 = Member.objects.create(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-membership": self.membership.pk,
            "form-0-organization": m1.organization.pk,
            "form-0-role": m1.role.pk,
            "form-0-id": m1.pk,
        }
        response = self.client.post(
            reverse("membership_members", args=[self.membership.pk]),
            data=data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("membership_details", args=[self.membership.pk])
        )
        self.assertEqual(list(self.membership.organizations.all()), [self.org_alpha])


class TestMemberUnique(MembershipTestMixin, TestBase):
    def test_duplicate_members_with_the_same_role_fail(self):
        """Duplicate Member & Role should fail for given membership."""
        # Arrange
        self.setUpMembership(consortium=True)
        member1 = Member(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        member2 = Member(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        # Act
        member1.save()

        # Assert
        with self.assertRaises(IntegrityError):
            member2.save()

    def test_distinct_members_for_the_same_membership(self):
        """Distinct Member & Role should work for given membership."""
        # Arrange
        self.setUpMembership(consortium=True)
        member1 = Member(
            organization=self.org_alpha,
            membership=self.membership,
            role=self.member_role,
        )

        member2 = Member(
            organization=self.org_beta,
            membership=self.membership,
            role=self.member_role,
        )

        member3 = Member(
            organization=self.org_alpha,
            membership=self.membership,
            role=MemberRole.objects.last(),
        )

        # Act & Assert
        member1.save()
        member2.save()
        member3.save()
