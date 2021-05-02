# coding: utf-8

from datetime import date, datetime, timezone
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from django.core.validators import ValidationError
from django.urls import reverse
from django_comments.models import Comment
from reversion.models import Version
from reversion.revisions import create_revision
from social_django.models import UserSocialAuth
import webtest
from webtest.forms import Upload

from consents.models import Consent, Term
from workshops.filters import filter_taught_workshops
from workshops.forms import PersonForm, PersonsMergeForm
from workshops.models import (
    Award,
    Badge,
    Event,
    KnowledgeDomain,
    Language,
    Organization,
    Person,
    Qualification,
    Role,
    Tag,
    Task,
    TrainingProgress,
    TrainingRequirement,
)
from workshops.tests.base import TestBase


@patch("workshops.github_auth.github_username_to_uid", lambda username: None)
class TestPerson(TestBase):
    """ Test cases for persons. """

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_family_name_notnull(self):
        """This is a regression test against #1682
        (https://github.com/carpentries/amy/issues/1682).

        The error was: family name was allowed to be null, which caused 500 errors
        when trying to save person without the family name.
        The actual error happened in the name normalization (util.normalize_name)."""
        p1 = Person.objects.create(personal="Harry", username="hp")
        p2 = Person.objects.create(personal="Hermione", username="hg")

        self.assertEqual(p1.family, "")
        self.assertEqual(p2.family, "")

    def test_login_with_email(self):
        """Make sure we can login with user's email too, not only with the
        username."""
        self.client.logout()
        email = "sudo@example.org"  # admin's email
        user = authenticate(username=email, password="admin")
        self.assertEqual(user, self.admin)

    def test_display_person_correctly_with_all_fields(self):
        response = self.client.get(
            reverse("person_details", args=[str(self.hermione.id)])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["person"], self.hermione)

    def test_display_person_correctly_with_some_fields(self):
        response = self.client.get(
            reverse("person_details", args=[str(self.ironman.id)])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["person"], self.ironman)

    def test_edit_person_email_when_all_fields_set(self):
        data = PersonForm(instance=self.ron).initial
        form = PersonForm(data, instance=self.ron)
        self.assertTrue(form.is_valid(), form.errors)

    def test_edit_person_email_when_airport_not_set(self):
        data = PersonForm(instance=self.spiderman).initial
        data["airport"] = ""
        form = PersonForm(data, instance=self.spiderman)
        self.assertTrue(form.is_valid(), form.errors)

    def test_edit_person_empty_family_name(self):
        data = {
            "family": "",  # family name cannot be empty
        }
        f = PersonForm(data)
        self.assertNotIn("family", f.errors)

    def test_1185_regression(self):
        """Ensure that admins without superuser privileges,
        but with 'change_person' permission can edit other people.

        Regression test against
        https://github.com/swcarpentry/amy/issues/1185."""

        manager = Person.objects.create_user(
            username="manager",
            personal="Manager",
            family="Manager",
            email="manager@example.org",
            password="manager",
        )
        can_change_person = Permission.objects.get(codename="change_person")
        manager.user_permissions.add(can_change_person)
        manager.data_privacy_agreement = True
        manager.save()
        bob = Person.objects.create_user(
            username="bob",
            personal="Bob",
            family="Smith",
            email="bob@example.org",
            password="bob",
        )

        bob_edit_url = reverse("person_edit", args=[bob.id])
        res = self.app.get(bob_edit_url, user="manager")
        self.assertEqual(res.status_code, 200)

    def test_person_award_badge(self):
        """Ensure that we can add an award from `person_edit` view"""
        url = reverse("person_edit", args=[self.spiderman.pk])
        person_edit = self.app.get(url, user="admin")
        award_form = person_edit.forms[2]
        award_form["award-badge"] = self.swc_instructor.pk

        self.assertEqual(self.spiderman.award_set.count(), 0)
        self.assertRedirects(award_form.submit(), url)
        self.assertEqual(self.spiderman.award_set.count(), 1)
        self.assertEqual(self.spiderman.award_set.first().badge, self.swc_instructor)

    def test_person_failed_training_warning(self):
        """
        Ensure that the form warns the admin if the person
        has a failed training, and an award or task is added
        """
        warning_popup = (
            'return confirm("Warning: Trainee failed previous training(s).'
            ' Are you sure you want to continue?");'
        )
        # No failed training, so no warning should show
        url = reverse("person_edit", args=[self.spiderman.pk])
        person_edit = self.app.get(url, user="admin")
        award_form = person_edit.forms[2]
        task_form = person_edit.forms[3]
        self.assertNotEqual(
            award_form.fields["submit"][0].attrs.get("onclick"), warning_popup
        )
        self.assertNotEqual(
            task_form.fields["submit"][0].attrs.get("onclick"), warning_popup
        )

        # Spiderman failed a training
        training = TrainingRequirement.objects.get(name="Training")
        TrainingProgress.objects.create(
            trainee=self.spiderman, state="f", requirement=training, notes="Failed"
        )

        # A warning should be shown
        url = reverse("person_edit", args=[self.spiderman.pk])
        person_edit = self.app.get(url, user="admin")
        award_form = person_edit.forms[2]
        task_form = person_edit.forms[3]
        self.assertEqual(award_form.fields["submit"][0].attrs["onclick"], warning_popup)
        self.assertEqual(task_form.fields["submit"][0].attrs["onclick"], warning_popup)

    def test_person_add_task(self):
        """Ensure that we can add a task from `person_edit` view"""
        self._setUpEvents()  # set up some events for us
        role = Role.objects.create(name="test_role")

        url = reverse("person_edit", args=[self.spiderman.pk])
        person_edit = self.app.get(url, user="admin")
        task_form = person_edit.forms[3]
        task_form["task-event"].force_value(Event.objects.first().pk)
        task_form["task-role"] = role.pk

        self.assertEqual(self.spiderman.task_set.count(), 0)
        self.assertRedirects(task_form.submit(), url)
        self.assertEqual(self.spiderman.task_set.count(), 1)
        self.assertEqual(self.spiderman.task_set.first().role, role)

    def test_edit_person_permissions(self):
        """ Make sure we can set up user permissions correctly. """

        # make sure Hermione does not have any perms, nor groups
        assert not self.hermione.is_superuser
        assert self.hermione.user_permissions.count() == 0
        assert self.hermione.groups.count() == 0

        user_permissions = Permission.objects.filter(content_type__app_label="admin")
        user_permissions_ids = user_permissions.values_list("id", flat=True).order_by(
            "id"
        )

        groups = Group.objects.all()
        groups_ids = groups.values_list("id", flat=True).order_by("id")

        data = {
            "is_superuser": True,
            "user_permissions": user_permissions_ids,
            "groups": groups_ids,
        }

        response = self.client.post(
            reverse("person_permissions", args=[self.hermione.id]),
            data,
        )

        assert response.status_code == 302

        self.hermione.refresh_from_db()
        assert self.hermione.is_superuser
        assert set(self.hermione.user_permissions.all()) == set(user_permissions)
        assert set(self.hermione.groups.all()) == set(groups)

    def test_delete_person(self):
        """Make sure deleted person is longer accessible.

        Additionally check on_delete behavior for Task, Qualification, and
        Award."""
        role = Role.objects.create(name="instructor")
        event = Event.objects.create(slug="test-event", host=self.org_alpha)
        people = [self.hermione, self.harry, self.ron]

        for person in people:
            # folks don't have any tasks by default, so let's add one
            person.task_set.create(event=event, role=role)

            awards = person.award_set.all()
            qualifications = person.qualification_set.all()
            tasks = person.task_set.all()

            # first we need to remove all tasks, qualifications and awards
            # because they're protected from deletion of Person
            # (on_delete=PROTECT)
            person.task_set.all().delete()
            person.qualification_set.all().delete()
            person.award_set.all().delete()

            rv = self.client.post(reverse("person_delete", args=[person.pk]))
            self.assertEqual(rv.status_code, 302)

            with self.assertRaises(Person.DoesNotExist):
                Person.objects.get(pk=person.pk)

            for award in awards:
                with self.assertRaises(Award.DoesNotExist):
                    Award.objects.get(pk=award.pk)
            for qualification in qualifications:
                with self.assertRaises(Qualification.DoesNotExist):
                    Qualification.objects.get(pk=qualification.pk)
            for task in tasks:
                with self.assertRaises(Task.DoesNotExist):
                    Task.objects.get(pk=task.pk)

    def test_editing_qualifications(self):
        """Make sure we can edit user lessons without any issues."""
        assert set(self.hermione.lessons.all()) == {self.git, self.sql}

        url = reverse("person_edit", args=[self.hermione.pk])
        data = PersonForm(instance=self.hermione).initial
        data["lessons"] = [self.git.pk]

        response = self.client.post(url, data)
        assert response.status_code == 302
        assert set(self.hermione.lessons.all()) == {self.git}

    def test_person_add_lessons(self):
        """Check if it's still possible to add lessons via PersonCreate
        view."""
        data = {
            "username": "test",
            "personal": "Test",
            "family": "Test",
            "gender": "U",
            "lessons": [1, 2],  # just IDs
        }
        rv = self.client.post(reverse("person_add"), data)
        assert rv.status_code == 302

        # make sure "no lessons" works too
        data = {
            "username": "test2",
            "personal": "Test",
            "family": "Test",
            "gender": "U",
            "lessons": [],
        }
        rv = self.client.post(reverse("person_add"), data)
        assert rv.status_code == 302

    def test_person_success_message(self):
        """Since PersonCreate view simulates SuccessMessageMixin, check if it
        does it correctly."""
        data = {
            "username": "test",
            "personal": "Test",
            "family": "Test",
            "gender": "U",
            "lessons": [1, 2],  # just IDs
        }
        rv = self.client.post(reverse("person_add"), data, follow=True)
        assert rv.status_code == 200
        content = rv.content.decode("utf-8")
        assert "Test Test was created successfully." in content

    def test_person_username_validation(self):
        """Ensure username doesn't allow for non-ASCII characters."""
        invalid_usernames = ["Zażółć gęślą jaźń", "chrząszcz"]
        for username in invalid_usernames:
            with self.subTest(username=username):
                person = Person.objects.create(
                    personal="Testing",
                    family="Testing",
                    username=username,
                )
                with self.assertRaises(ValidationError) as cm:
                    person.clean_fields(exclude=["password"])
                self.assertIn("username", cm.exception.message_dict)

        valid_username = "blanking-crush_andy"
        person = Person.objects.create(
            personal="Andy",
            family="Blanking-Crush",
            username=valid_username,
        )
        person.clean_fields(exclude=["password"])

    def test_new_person_auto_username(self):
        """Ensure after adding a new person, they're automatically assigned
        a unique username."""
        url = reverse("person_add")
        data = {
            "personal": "Albert",
            "family": "Einstein",
            "gender": "U",
        }
        self.client.post(url, data)
        Person.objects.get(
            personal="Albert", family="Einstein", username="einstein_albert"
        )

    def test_person_email_auto_lowercase(self):
        """Make sure PersonForm/PersonCreateForm lowercases user's email."""
        data = {
            "username": "curie_marie",
            "personal": "Marie",
            "family": "Curie",
            "gender": "F",
            "email": "M.CURIE@sorbonne.fr",
        }
        url = reverse("person_add")
        self.client.post(url, data)
        person = Person.objects.get(username="curie_marie")
        self.assertEqual(person.email, "m.curie@sorbonne.fr")

        url = reverse("person_edit", args=[person.pk])
        self.client.post(url, data)
        person.refresh_from_db()
        self.assertEqual(person.email, "m.curie@sorbonne.fr")

    def test_edit_permission_of_person_without_email(self):
        """
        Creating a person without email id and then changing
        the permissions for that person.
        """
        p = Person.objects.create(personal="P1", family="P1")
        response = self.client.get(reverse("person_details", args=[str(p.id)]))
        assert response.status_code == 200

        user_permissions = Permission.objects.filter(content_type__app_label="admin")
        user_permissions_ids = user_permissions.values_list("id", flat=True).order_by(
            "id"
        )

        groups = Group.objects.all()
        groups_ids = groups.values_list("id", flat=True).order_by("id")

        data = {
            "is_superuser": True,
            "user_permissions": user_permissions_ids,
            "groups": groups_ids,
        }

        response = self.client.post(
            reverse("person_permissions", args=[str(p.id)]),
            data,
        )
        assert response.status_code == 302

    def test_get_training_tasks(self):
        p1 = Person.objects.create(username="p1")
        p2 = Person.objects.create(username="p2")
        org = Organization.objects.create(
            domain="example.com", fullname="Test Organization"
        )
        ttt, _ = Tag.objects.get_or_create(name="TTT")
        learner, _ = Role.objects.get_or_create(name="learner")
        other_role, _ = Role.objects.get_or_create(name="other role")
        e1 = Event.objects.create(slug="training", host=org)
        e1.tags.add(ttt)
        e2 = Event.objects.create(slug="workshop", host=org)
        e3 = Event.objects.create(slug="second-training", host=org)
        e3.tags.add(ttt)

        t1 = Task.objects.create(person=p1, event=e1, role=learner)

        # Tasks with event missing 'TTT' tag are ignored
        Task.objects.create(person=p1, event=e2, role=learner)

        # Tasks with role different than 'learner' are ignored
        Task.objects.create(person=p1, event=e3, role=other_role)

        # Tasks belonging to other people should be ignored
        Task.objects.create(person=p2, event=e1, role=learner)

        self.assertEqual(set(p1.get_training_tasks()), {t1})

    def test_awarding_instructor_badge_workflow(self):
        """Test that you can click "SWC" and "DC" labels in "eligible"
        column in trainees list view. When you click them, you're moved to
        the view where you can edit person's awards. "Award" and "event"
        field should be prefilled in. Also test if you're moved back to
        trainees view after adding the badge."""

        trainee = Person.objects.create_user(
            username="trainee",
            personal="Bob",
            family="Smith",
            email="bob.smith@example.com",
        )
        host = Organization.objects.create(
            domain="example.com", fullname="Test Organization"
        )
        ttt, _ = Tag.objects.get_or_create(name="TTT")
        learner, _ = Role.objects.get_or_create(name="learner")
        training = Event.objects.create(slug="2016-08-10-training", host=host)
        training.tags.add(ttt)
        Task.objects.create(person=trainee, event=training, role=learner)

        trainees = self.app.get(reverse("all_trainees"), user="admin")

        # clear trainee awards so that .last() always returns the exact badge
        # we want
        trainee.award_set.all().delete()

        # Test workflow starting from clicking at "instructor badge" label
        swc_res = trainees.click("^<strike>instructor badge</strike>$")
        self.assertSelected(swc_res.forms["main-form"]["award-badge"], "---------")
        self.assertEqual(
            int(swc_res.forms["main-form"]["award-event"].value), training.pk
        )
        swc_res.forms["main-form"]["award-badge"].select(self.swc_instructor.pk)
        res = swc_res.forms["main-form"].submit()
        self.assertRedirects(res, reverse("all_trainees"))
        self.assertEqual(trainee.award_set.last().badge, self.swc_instructor)

        # clear trainee awards so that .last() always returns the exact badge
        # we want
        trainee.award_set.all().delete()

        # Test workflow starting from clicking at "instructor badge" label
        dc_res = trainees.click("^<strike>instructor badge</strike>$")
        self.assertSelected(dc_res.forms["main-form"]["award-badge"], "---------")
        self.assertEqual(
            int(dc_res.forms["main-form"]["award-event"].value), training.pk
        )
        dc_res.forms["main-form"]["award-badge"].select(self.dc_instructor.pk)
        res = dc_res.forms["main-form"].submit()
        self.assertRedirects(res, reverse("all_trainees"))
        self.assertEqual(trainee.award_set.last().badge, self.dc_instructor)

    def test_person_github_username_validation(self):
        """Ensure GitHub username doesn't allow for spaces or commas."""
        invalid_usernames = ["Harry James Potter", "Harry, Hermione, Ron"]
        for key, username in enumerate(invalid_usernames):
            with self.subTest(username=username):
                person = Person.objects.create(
                    personal="Testing",
                    family="Testing",
                    username="testing{}".format(key),
                    github=username,
                )
                with self.assertRaises(ValidationError) as cm:
                    person.clean_fields(exclude=["password"])
                self.assertIn("github", cm.exception.message_dict)

        valid_username = "blanking-crush-andy"
        person = Person.objects.create(
            personal="Andy",
            family="Blanking-Crush",
            username="blanking-crush_andy",
            github=valid_username,
        )
        person.clean_fields(exclude=["password"])

    def test_creating_person_with_no_comment(self):
        """Ensure that no comment is added when PersonCreateForm without comment
        content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "username": "curie_marie",
            "personal": "Marie",
            "family": "Curie",
            "gender": "F",
            "email": "m.curie@sorbonne.fr",
            "comment": "",
        }
        url = reverse("person_add")
        self.client.post(url, data)
        Person.objects.get(username="curie_marie")
        self.assertEqual(Comment.objects.count(), 0)

    def test_creating_person_with_comment(self):
        """Ensure that a comment is added when PersonCreateForm with comment
        content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "username": "curie_marie",
            "personal": "Marie",
            "family": "Curie",
            "gender": "F",
            "email": "m.curie@sorbonne.fr",
            "comment": "This is a test comment.",
        }
        url = reverse("person_add")
        self.client.post(url, data)
        obj = Person.objects.get(username="curie_marie")
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.comment, "This is a test comment.")
        self.assertIn(comment, Comment.objects.for_model(obj))


class TestPersonPassword(TestBase):
    """Separate tests for testing password setting.

    They need to be in separate class that doesn't call
    self._setUpUsersAndLogin().
    """

    def setUp(self):
        admins, _ = Group.objects.get_or_create(name="administrators")

        # create a superuser
        self.admin = Person.objects.create_superuser(
            username="admin",
            personal="Super",
            family="User",
            email="sudo@example.org",
            password="admin",
        )
        self.admin.data_privacy_agreement = True
        self.admin.save()

        # create a normal user
        self.user = Person.objects.create_user(
            username="user",
            personal="Typical",
            family="User",
            email="undo@example.org",
            password="user",
        )
        self.user.data_privacy_agreement = True
        self.user.save()
        self.user.groups.add(admins)

    def test_edit_password_by_superuser(self):
        self.client.login(username="admin", password="admin")
        user = self.admin
        url = reverse("person_password", args=[user.pk])
        doc = self.client.get(url)
        form = doc.context["form"]

        # check that correct form is rendered
        self.assertNotIn("old_password", form.fields)
        self.assertIn("new_password1", form.fields)
        self.assertIn("new_password2", form.fields)

        # try incorrect form data first
        new_password = "new_password"
        data = {
            "new_password1": new_password,
            "new_password2": "asdf",
        }
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        # update password
        data["new_password2"] = new_password
        rv = self.client.post(url, data)
        assert rv.status_code == 302

        # make sure password was updated
        user.refresh_from_db()
        assert user.check_password(new_password) is True

    def test_edit_other_user_password_by_superuser(self):
        self.client.login(username="admin", password="admin")
        user = self.user
        url = reverse("person_password", args=[user.pk])
        doc = self.client.get(url)
        form = doc.context["form"]

        # check that correct form is rendered
        self.assertNotIn("old_password", form.fields)
        self.assertIn("new_password1", form.fields)
        self.assertIn("new_password2", form.fields)

        # try incorrect form data first
        new_password = "new_password"
        data = {
            "new_password1": new_password,
            "new_password2": "asdf",
        }
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        # update password
        data["new_password2"] = new_password
        rv = self.client.post(url, data)
        assert rv.status_code == 302

        # make sure password was updated
        user.refresh_from_db()
        assert user.check_password(new_password) is True

    def test_edit_password_by_normal_user(self):
        self.client.login(username="user", password="user")
        user = self.user
        url = reverse("person_password", args=[user.pk])
        doc = self.client.get(url)
        form = doc.context["form"]

        # check that correct form is rendered
        self.assertIn("old_password", form.fields)
        self.assertIn("new_password1", form.fields)
        self.assertIn("new_password2", form.fields)

        # try incorrect form data first
        new_password = "new_password"
        data = {
            "old_password": "asdf",
            "new_password1": new_password,
            "new_password2": "asdhaf",
        }
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        # try correct old password
        data["old_password"] = "user"
        rv = self.client.post(url, data)
        assert rv.status_code != 302

        # update password to a new matching password
        data["new_password2"] = new_password
        rv = self.client.post(url, data)
        assert rv.status_code == 302

        # make sure password was updated
        user.refresh_from_db()
        assert user.check_password(new_password) is True

    def test_edit_other_user_password_by_normal_user(self):
        self.client.login(username="user", password="user")
        user = self.admin
        rv = self.client.get(reverse("person_password", args=[user.pk]))
        assert rv.status_code == 403


class TestPersonMerging(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpBadges()
        self._setUpLessons()
        self._setUpRoles()
        self._setUpEvents()
        self._setUpUsersAndLogin()

        # create training requirement
        self.training = TrainingRequirement.objects.get(name="Training")
        self.homework = TrainingRequirement.objects.get(name="SWC Homework")

        # create first person
        self.person_a = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            may_contact=True,
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        self.person_a.award_set.create(
            badge=self.swc_instructor, awarded=date(2016, 2, 16)
        )
        Qualification.objects.create(person=self.person_a, lesson=self.git)
        Qualification.objects.create(person=self.person_a, lesson=self.sql)
        self.person_a.domains.set([KnowledgeDomain.objects.first()])
        self.person_a.task_set.create(
            event=Event.objects.get(slug="ends-tomorrow-ongoing"),
            role=Role.objects.get(name="instructor"),
        )
        self.person_a.languages.set([Language.objects.first(), Language.objects.last()])
        self.person_a.trainingprogress_set.create(requirement=self.training)

        # comments made by this person
        self.ca_1 = Comment.objects.create(
            content_object=self.admin,
            user=self.person_a,
            comment="Comment from person_a on admin",
            submit_date=datetime.now(tz=timezone.utc),
            site=Site.objects.get_current(),
        )
        # comments regarding this person
        self.ca_2 = Comment.objects.create(
            content_object=self.person_a,
            user=self.admin,
            comment="Comment from admin on person_a",
            submit_date=datetime.now(tz=timezone.utc),
            site=Site.objects.get_current(),
        )

        # create second person
        self.person_b = Person.objects.create(
            personal="Jayden",
            middle="",
            family="Deckow",
            username="deckow_jayden",
            email="deckow.jayden@example.com",
            secondary_email="notused@example.org",
            gender="M",
            may_contact=True,
            airport=self.airport_0_50,
            github="deckow_jayden",
            twitter="deckow_jayden",
            url="http://jaydendeckow.com/",
            affiliation="UFlo",
            occupation="Staff",
            orcid="0000-0000-0001",
            is_active=True,
        )
        self.person_b.award_set.create(
            badge=self.dc_instructor, awarded=date(2016, 2, 16)
        )
        Qualification.objects.create(person=self.person_b, lesson=self.sql)
        self.person_b.domains.set([KnowledgeDomain.objects.last()])
        self.person_b.languages.set([Language.objects.last()])
        self.person_b.trainingprogress_set.create(requirement=self.training)
        self.person_b.trainingprogress_set.create(requirement=self.homework)

        # comments made by this person
        self.cb_1 = Comment.objects.create(
            content_object=self.admin,
            user=self.person_b,
            comment="Comment from person_b on admin",
            submit_date=datetime.now(tz=timezone.utc),
            site=Site.objects.get_current(),
        )
        # comments regarding this person
        self.cb_2 = Comment.objects.create(
            content_object=self.person_b,
            user=self.admin,
            comment="Comment from admin on person_b",
            submit_date=datetime.now(tz=timezone.utc),
            site=Site.objects.get_current(),
        )

        # set up a strategy
        self.strategy = {
            "person_a": self.person_a.pk,
            "person_b": self.person_b.pk,
            "id": "obj_b",
            "username": "obj_a",
            "personal": "obj_b",
            "middle": "obj_a",
            "family": "obj_a",
            "email": "obj_b",
            "secondary_email": "obj_b",
            "may_contact": "obj_a",
            "publish_profile": "obj_a",
            "data_privacy_agreement": "obj_b",
            "gender": "obj_b",
            "gender_other": "obj_b",
            "airport": "obj_a",
            "github": "obj_b",
            "twitter": "obj_a",
            "url": "obj_b",
            "affiliation": "obj_b",
            "occupation": "obj_a",
            "orcid": "obj_b",
            "award_set": "obj_a",
            "qualification_set": "obj_b",
            "domains": "combine",
            "languages": "combine",
            "task_set": "obj_b",
            "is_active": "obj_a",
            "trainingprogress_set": "combine",
            "comment_comments": "combine",  # made by this person
            "comments": "combine",  # regarding this person
        }
        base_url = reverse("persons_merge")
        query = urlencode({"person_a": self.person_a.pk, "person_b": self.person_b.pk})
        self.url = "{}?{}".format(base_url, query)

    def test_form_invalid_values(self):
        """Make sure only a few fields accept third option ("combine")."""
        hidden = {
            "person_a": self.person_a.pk,
            "person_b": self.person_b.pk,
        }
        # fields accepting only 2 options: "obj_a" and "obj_b"
        failing = {
            "id": "combine",
            "username": "combine",
            "personal": "combine",
            "middle": "combine",
            "family": "combine",
            "email": "combine",
            "secondary_email": "combine",
            "may_contact": "combine",
            "publish_profile": "combine",
            "data_privacy_agreement": "combine",
            "gender": "combine",
            "gender_other": "combine",
            "airport": "combine",
            "github": "combine",
            "twitter": "combine",
            "url": "combine",
            "affiliation": "combine",
            "occupation": "combine",
            "orcid": "combine",
            "is_active": "combine",
        }
        # fields additionally accepting "combine"
        passing = {
            "award_set": "combine",
            "qualification_set": "combine",
            "domains": "combine",
            "languages": "combine",
            "task_set": "combine",
            "trainingprogress_set": "combine",
            "comment_comments": "combine",
            "comments": "combine",
        }
        data = hidden.copy()
        data.update(failing)
        data.update(passing)

        form = PersonsMergeForm(data)
        self.assertFalse(form.is_valid())

        for key in failing:
            self.assertIn(key, form.errors)
        for key in passing:
            self.assertNotIn(key, form.errors)

        # make sure no fields are added without this test being updated
        self.assertEqual(set(list(form.fields.keys())), set(list(data.keys())))

    def test_merging_base_person(self):
        """Merging: ensure the base person is selected based on ID form
        field.

        If ID field has a value of 'obj_b', then person B is base event and it
        won't be removed from the database after the merge. Person A, on the
        other hand, will."""
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)

        self.person_b.refresh_from_db()
        with self.assertRaises(Person.DoesNotExist):
            self.person_a.refresh_from_db()

    def test_merging_basic_attributes(self):
        """Merging: ensure basic (non-relationships) attributes are properly
        saved."""
        assertions = {
            "id": self.person_b.id,
            "username": self.person_a.username,
            "personal": self.person_b.personal,
            "middle": self.person_a.middle,
            "family": self.person_a.family,
            "email": self.person_b.email,
            "secondary_email": self.person_b.secondary_email,
            "may_contact": self.person_a.may_contact,
            "gender": self.person_b.gender,
            "gender_other": self.person_b.gender_other,
            "airport": self.person_a.airport,
            "github": self.person_b.github,
            "twitter": self.person_a.twitter,
            "url": self.person_b.url,
            "affiliation": self.person_b.affiliation,
            "occupation": self.person_a.occupation,
            "orcid": self.person_b.orcid,
            "is_active": self.person_a.is_active,
        }
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(getattr(self.person_b, key), value, key)

    def test_merging_relational_attributes(self):
        """Merging: ensure M2M-related fields are properly saved/combined."""
        assertions = {
            # instead testing awards, let's simply test badges
            "badges": set(Badge.objects.filter(name="swc-instructor")),
            # we're saving/combining qualifications, but it affects lessons
            "lessons": {self.sql},
            "domains": {
                KnowledgeDomain.objects.first(),
                KnowledgeDomain.objects.last(),
            },
            "languages": {Language.objects.first(), Language.objects.last()},
            "task_set": set(Task.objects.none()),
            # Combining similar TrainingProgresses should end up in
            # a unique constraint violation, shouldn't it?
            "trainingprogress_set": set(TrainingProgress.objects.all()),
            "comment_comments": set([self.ca_1, self.cb_1]),
        }

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(set(getattr(self.person_b, key).all()), value, key)

    def test_merging_m2m_attributes(self):
        """Merging: ensure M2M-related fields are properly saved/combined.
        This is a regression test; we have to ensure that M2M objects aren't
        removed from the database."""
        assertions = {
            # instead testing awards, let's simply test badges
            "badges": set(Badge.objects.filter(name="swc-instructor")),
            # we're saving/combining qualifications, but it affects lessons
            "lessons": {self.sql, self.git},
            "domains": {
                KnowledgeDomain.objects.first(),
                KnowledgeDomain.objects.last(),
            },
        }
        self.strategy["qualification_set"] = "obj_a"

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(set(getattr(self.person_b, key).all()), value, key)

    def test_merging_m2m_with_similar_attributes(self):
        """Regression test: merging people with the same M2M objects, e.g. when
        both people have task 'learner' in event 'ABCD', would result in unique
        constraint violation and cause IntegrityError."""
        self.person_b.task_set.create(
            event=Event.objects.get(slug="ends-tomorrow-ongoing"),
            role=Role.objects.get(name="instructor"),
        )

        self.strategy["task_set"] = "combine"

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)

    def test_merging_comments_strategy1(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 1 (combine)."""
        self.strategy["comments"] = "combine"
        comments = [self.ca_2, self.cb_2]
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.person_b).filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy2(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 2 (object a)."""
        self.strategy["comments"] = "obj_a"
        comments = [self.ca_2]
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.person_b).filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy3(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 3 (object b)."""
        self.strategy["comments"] = "obj_b"
        comments = [self.cb_2]
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.person_b.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.person_b).filter(is_removed=False)),
            set(comments),
        )


def github_username_to_uid_mock(username):
    username2uid = {
        "username": "1",
        "changed": "2",
        "changedagain": "3",
    }
    return username2uid[username]


class TestPersonAndUserSocialAuth(TestBase):
    """ Test Person.synchronize_usersocialauth and Person.save."""

    @patch("workshops.github_auth.github_username_to_uid", github_username_to_uid_mock)
    def test_basic(self):
        user = Person.objects.create_user(
            username="user",
            personal="Typical",
            family="User",
            email="undo@example.org",
            password="user",
        )

        # Syncing UserSocialAuth for a user without GitHub username should
        # not create any UserSocialAuth record.
        user.github = ""
        user.save()
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list("provider", "uid", "user")
        expected = []
        self.assertSequenceEqual(got, expected)

        # UserSocialAuth record should be created for a user with GitHub
        # username.
        user.github = "username"
        user.save()
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list("provider", "uid", "user")
        expected = [("github", "1", user.pk)]
        self.assertSequenceEqual(got, expected)

        # When GitHub username is changed, Person.save should take care of
        # clearing UserSocialAuth table.
        user.github = "changed"
        user.save()

        expected = []
        got = UserSocialAuth.objects.values_list("provider", "uid", "user")
        self.assertSequenceEqual(got, expected)

        # Syncing UserSocialAuth should result in a new UserSocialAuth record.
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list("provider", "uid", "user")
        expected = [("github", "2", user.pk)]
        self.assertSequenceEqual(got, expected)

        # Syncing UserSocialAuth after changing GitHub username without
        # saving should also result in updated UserSocialAuth.
        user.github = "changedagain"
        # no user.save()
        user.synchronize_usersocialauth()

        got = UserSocialAuth.objects.values_list("provider", "uid", "user")
        expected = [("github", "3", user.pk)]
        self.assertSequenceEqual(got, expected)

    def test_errors_are_not_hidden(self):
        """Test that errors occuring in synchronize_usersocialauth are not
        hidden, that is you're not redirected to any other view. Regression
        for #890."""

        self._setUpUsersAndLogin()
        with patch.object(
            Person, "synchronize_usersocialauth", side_effect=NotImplementedError
        ):
            with self.assertRaises(NotImplementedError):
                self.client.get(reverse("sync_usersocialauth", args=(self.admin.pk,)))


class TestGetMissingSWCInstructorRequirements(TestBase):
    def setUp(self):
        self.person = Person.objects.create(username="person")
        self.training = TrainingRequirement.objects.get(name="Training")
        self.swc_homework = TrainingRequirement.objects.get(name="SWC Homework")
        self.dc_homework = TrainingRequirement.objects.get(name="DC Homework")
        self.discussion = TrainingRequirement.objects.get(name="Discussion")
        self.swc_demo = TrainingRequirement.objects.get(name="SWC Demo")
        self.dc_demo = TrainingRequirement.objects.get(name="DC Demo")

    def test_all_requirements_satisfied(self):
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.training
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.swc_homework
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.discussion
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.swc_demo
        )

        person = Person.objects.annotate_with_instructor_eligibility().get(
            username="person"
        )
        self.assertEqual(person.get_missing_instructor_requirements(), [])

    def test_some_requirements_are_fulfilled(self):
        # Homework was accepted, the second time.
        TrainingProgress.objects.create(
            trainee=self.person, state="f", requirement=self.swc_homework
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.swc_homework
        )
        # Dc-demo records should be ignored
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.dc_demo
        )
        # Not passed progress should be ignored.
        TrainingProgress.objects.create(
            trainee=self.person, state="f", requirement=self.swc_demo
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="n", requirement=self.discussion
        )
        # Passed discarded progress should be ignored.
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.training, discarded=True
        )

        person = Person.objects.annotate_with_instructor_eligibility().get(
            username="person"
        )
        self.assertEqual(
            person.get_missing_instructor_requirements(), ["Training", "Discussion"]
        )

    def test_none_requirement_is_fulfilled(self):
        person = Person.objects.annotate_with_instructor_eligibility().get(
            username="person"
        )
        self.assertEqual(
            person.get_missing_instructor_requirements(),
            ["Training", "Homework (SWC/DC/LC)", "Discussion", "Demo (SWC/DC/LC)"],
        )


class TestGetMissingDCInstructorRequirements(TestBase):
    def setUp(self):
        self.person = Person.objects.create(username="person")
        self.training = TrainingRequirement.objects.get(name="Training")
        self.swc_homework = TrainingRequirement.objects.get(name="SWC Homework")
        self.dc_homework = TrainingRequirement.objects.get(name="DC Homework")
        self.discussion = TrainingRequirement.objects.get(name="Discussion")
        self.swc_demo = TrainingRequirement.objects.get(name="SWC Demo")
        self.dc_demo = TrainingRequirement.objects.get(name="DC Demo")

    def test_all_requirements_satisfied(self):
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.training
        )

        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.dc_homework
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.discussion
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.dc_demo
        )

        person = Person.objects.annotate_with_instructor_eligibility().get(
            username="person"
        )
        self.assertEqual(person.get_missing_instructor_requirements(), [])

    def test_some_requirements_are_fulfilled(self):
        # Homework was accepted, the second time.
        TrainingProgress.objects.create(
            trainee=self.person, state="f", requirement=self.dc_homework
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.dc_homework
        )
        # Swc-demo should be ignored
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.swc_demo
        )
        # Not passed progress should be ignored.
        TrainingProgress.objects.create(
            trainee=self.person, state="f", requirement=self.dc_demo
        )
        TrainingProgress.objects.create(
            trainee=self.person, state="n", requirement=self.discussion
        )
        # Passed discarded progress should be ignored.
        TrainingProgress.objects.create(
            trainee=self.person, state="p", requirement=self.training, discarded=True
        )

        person = Person.objects.annotate_with_instructor_eligibility().get(
            username="person"
        )
        self.assertEqual(
            person.get_missing_instructor_requirements(), ["Training", "Discussion"]
        )

    def test_none_requirement_is_fulfilled(self):
        person = Person.objects.annotate_with_instructor_eligibility().get(
            username="person"
        )
        self.assertEqual(
            person.get_missing_instructor_requirements(),
            ["Training", "Homework (SWC/DC/LC)", "Discussion", "Demo (SWC/DC/LC)"],
        )


class TestFilterTaughtWorkshops(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpBadges()
        self._setUpLessons()
        self._setUpTags()
        self._setUpRoles()
        self._setUpInstructors()
        self._setUpNonInstructors()

    def test_bug_975(self):
        test_host = Organization.objects.create(
            domain="example.com", fullname="Test Organization"
        )
        ttt = Tag.objects.get(name="TTT")
        swc = Tag.objects.get(name="SWC")

        e1 = Event.objects.create(slug="ttt-event", host=test_host)
        e1.tags.add(ttt)
        e2 = Event.objects.create(slug="swc-event", host=test_host)
        e2.tags.add(swc)
        e3 = Event.objects.create(slug="second-ttt-event", host=test_host)
        e3.tags.add(ttt)

        Task.objects.create(
            role=Role.objects.get(name="instructor"), person=self.hermione, event=e1
        )
        Task.objects.create(
            role=Role.objects.get(name="learner"), person=self.harry, event=e1
        )
        Task.objects.create(
            role=Role.objects.get(name="instructor"), person=self.ron, event=e2
        )
        Task.objects.create(
            role=Role.objects.get(name="learner"), person=self.spiderman, event=e2
        )
        Task.objects.create(
            role=Role.objects.get(name="instructor"), person=self.hermione, event=e3
        )

        qs = Person.objects.all()
        filtered = filter_taught_workshops(qs, "", [ttt.pk])

        # - Hermione should be listed only once even though she was an
        # instructor at two TTT events.
        #
        # - Harry should not be listed, because he was a learner, not an
        # instructor.
        #
        # - Ron and Spiderman should not be listed, because they didn't
        # participated in a TTT event.
        self.assertSequenceEqual(filtered, [self.hermione])


class TestPersonUpdateViewPermissions(TestBase):
    def setUp(self):
        self.trainee = Person.objects.create_user(
            "trainee", "Harry", "Potter", "hp@mail.com", "hp"
        )
        self.trainer = Person.objects.create_user(
            "trainer", "Severus", "Snape", "ss@mail.com", "ss"
        )
        self.trainer.data_privacy_agreement = True
        self.trainer.save()
        trainer_group, _ = Group.objects.get_or_create(name="trainers")
        self.trainer.groups.add(trainer_group)

    def test_correct_permissions(self):
        self.assertTrue(self.trainer.is_admin)
        self.assertFalse(self.trainee.is_admin)

    def test_trainer_can_edit_self_profile(self):
        profile_edit = self.app.get(
            reverse("person_edit", args=[self.trainer.pk]),
            user=self.trainer,
        )
        self.assertEqual(profile_edit.status_code, 200)

    def test_trainer_cannot_edit_stray_profile(self):
        with self.assertRaises(webtest.app.AppError):
            self.app.get(
                reverse("person_edit", args=[self.trainee.pk]),
                user=self.trainer,
            )


class TestRegression1076(TestBase):
    """Family name should be optional."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpEvents()

    def test_family_name_is_optional(self):
        self.admin.family = ""
        self.admin.save()  # no error should be raised
        self.admin.full_clean()  # no error should be raised

    def test_bulk_upload(self):
        event_slug = Event.objects.first().slug
        csv = (
            "personal,family,email,event,role\n" "John,,john@smith.com,{0},learner\n"
        ).format(event_slug)

        upload_page = self.app.get(reverse("person_bulk_add"), user="admin")
        upload_form = upload_page.forms["main-form"]
        upload_form["file"] = Upload("people.csv", csv.encode("utf-8"))

        confirm_page = upload_form.submit().maybe_follow()
        confirm_form = confirm_page.forms["main-form"]

        info_page = confirm_form.submit("confirm").maybe_follow()
        self.assertIn("Successfully created 1 persons and 1 tasks", info_page)
        john_created = Person.objects.filter(personal="John", family="").exists()
        self.assertTrue(john_created)


class TestArchivePerson(TestBase):
    """ Test cases for person archive endpoint. """

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()
        self.role = Role.objects.create(name="instructor")
        self.event = Event.objects.create(slug="test-event", host=self.org_alpha)
        # create a normal user
        self.user = Person.objects.create_user(
            username="user",
            personal="",
            family="",
            email="user@example.org",
            password="pass",
        )
        self.user.data_privacy_agreement = True
        self.user.save()
        # folks don't have any tasks by default, so let's add one
        self.harry.task_set.create(event=self.event, role=self.role)
        self.ron.task_set.create(event=self.event, role=self.role)
        self.hermione.task_set.create(event=self.event, role=self.role)
        self.admin.task_set.create(event=self.event, role=self.role)

        # Consent to active terms
        self.person_consent_active_terms(self.harry)
        self.person_consent_active_terms(self.ron)
        self.person_consent_active_terms(self.hermione)
        self.person_consent_active_terms(self.admin)
        self.active_terms = Term.objects.active()

    def assert_cannot_archive(self, person: Person) -> None:
        awards = person.award_set.all()
        qualifications = person.qualification_set.all()
        tasks = person.task_set.all()
        domains = person.domains.all()
        consents = Consent.objects.filter(person=person).active()

        rv = self.client.post(reverse("person_archive", args=[person.pk]))
        self.assertNotEqual(rv.status_code, 302)

        archived_profile = Person.objects.get(pk=person.pk)
        self.assertEqual(person, archived_profile)

        # Awards, tasks, and qualifications should be unchanged
        self.assertCountEqual(awards, archived_profile.award_set.all())
        self.assertCountEqual(tasks, archived_profile.task_set.all())
        self.assertCountEqual(qualifications, archived_profile.qualification_set.all())
        self.assertCountEqual(domains, archived_profile.domains.all())
        self.assertCountEqual(
            consents, Consent.objects.filter(person=archived_profile).active()
        )

    def assert_person_archive(self, person: Person) -> None:
        """
        Calls the Person Archive endpoint and asserts that the
        given Person has been archived.
        """
        awards = person.award_set.all()
        qualifications = person.qualification_set.all()
        tasks = person.task_set.all()
        domains = person.domains.all()

        rv = self.client.post(reverse("person_archive", args=[person.pk]))
        self.assertEqual(rv.status_code, 302)

        archived_profile = Person.objects.get(pk=person.pk)
        self._assert_personal_info_removed(archived_profile)

        # First name, last name, Awards, tasks, and qualifications should be unchanged
        self.assertEqual(archived_profile.personal, person.personal)
        self.assertEqual(archived_profile.family, person.family)
        self.assertEqual(archived_profile.middle, person.middle)
        self.assertEqual(archived_profile.username, person.username)
        self.assertCountEqual(awards, archived_profile.award_set.all())
        self.assertCountEqual(tasks, archived_profile.task_set.all())
        self.assertCountEqual(qualifications, archived_profile.qualification_set.all())
        self.assertCountEqual(domains, archived_profile.domains.all())

    def _assert_personal_info_removed(self, archived_profile: Person) -> None:
        """
        Used after calling person.archive()
        Asserts that all personal data about the user has been removed.
        """
        self.assertIsNone(archived_profile.email)
        self.assertEqual(archived_profile.country, "")
        self.assertIsNone(archived_profile.airport)
        self.assertIsNone(archived_profile.github)
        self.assertIsNone(archived_profile.twitter)
        self.assertEqual(archived_profile.url, "")
        self.assertEqual(archived_profile.user_notes, "")
        self.assertEqual(archived_profile.affiliation, "")
        self.assertFalse(archived_profile.is_active)
        self.assertEqual(archived_profile.occupation, "")
        self.assertEqual(archived_profile.orcid, "")
        # All Consents should be unset
        consents = Consent.objects.filter(person=archived_profile).active()
        self.assertEqual(len(self.active_terms), len(consents))
        self.assertFalse(consents.filter(term_option__isnull=False).exists())

    def test_archive_by_super_user(self):
        """
        Superusers should be able to archive any user.
        """
        # Login as Admin
        self.assertTrue(
            self.client.login(username=self.admin.username, password="admin")
        )

        # Admin should be able to archive other user's profile
        self.assert_person_archive(self.harry)
        self.assert_person_archive(self.ron)
        self.assert_person_archive(self.hermione)
        self.assert_person_archive(self.user)

        # Admin should be able to archive their own profile
        self.assert_person_archive(self.admin)

        # Archived admin should not be able to log in.
        self.assert_person_archive(self.admin)
        self.assertFalse(
            self.client.login(username=self.admin.username, password="admin")
        )

    def test_archive_by_non_admin(self):
        """
        Non-Admin users should be able to archive their own profiles.
        """
        # Login as a normal user
        assert not self.user.is_superuser
        self.assertTrue(self.client.login(username=self.user.username, password="pass"))

        # User (non-admin) should not be able to archive anyone else's profile
        self.assert_cannot_archive(self.ron)
        self.assert_cannot_archive(self.hermione)
        self.assert_cannot_archive(self.harry)
        self.assert_cannot_archive(self.admin)

        # User (non-admin) should be able to archive his own profile
        self.assert_person_archive(self.user)

        # Archived User should not be able to log in.
        self.assertFalse(
            self.client.login(username=self.user.username, password="pass")
        )

    def test_version_history_removed_when_archived(self) -> None:
        # Create the person and change their information a few times.
        with create_revision():
            person = Person.objects.create(
                personal="Draco",
                family="Malfoy",
                username="dmalfoy",
                email="draco@malfoy.com",
            )
        with create_revision():
            person.twitter = "dmalfoy"
            person.save()
        with create_revision():
            person.github = "dmalfoy"
            person.save()

        # get the current profile change history
        original_versions = Version.objects.get_for_object(person)
        self.assertEqual(len(original_versions), 3)

        # Login as a normal user (non-admin)
        # This user should not be able to archive anyone else's profile
        # Profile edit history should be unchanged
        assert not self.user.is_superuser
        self.assertTrue(self.client.login(username=self.user.username, password="pass"))
        self.assert_cannot_archive(person)
        self.assertCountEqual(original_versions, Version.objects.get_for_object(person))

        # Login as the admin user and archive the profile
        # All profile change history after archival
        # should be removed but the current one
        self.assertTrue(
            self.client.login(username=self.admin.username, password="admin")
        )
        self.assert_person_archive(person)
        archived_profile = Person.objects.get(pk=person.pk)
        versions_after_archive = Version.objects.get_for_object(archived_profile)
        self.assertEqual(len(versions_after_archive), 1)
