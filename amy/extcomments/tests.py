from django.test import TestCase
from django.urls import reverse
import django_comments

from workshops.models import Organization, Person

from .utils import add_comment_for_object


class TestCommentForObjectUtil(TestCase):
    def test_util(self):
        # Arrange
        person = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="rw",
            is_active=True,
            email="",
            data_privacy_agreement=True,
        )
        organization = Organization.objects.create(
            domain="example.org",
            fullname="Example Organisation",
        )
        content = "Test comment"
        CommentModel = django_comments.get_model()

        # Act
        comment = add_comment_for_object(organization, person, content)

        # Assert
        self.assertEqual(list(CommentModel.objects.for_model(organization)), [comment])


class TestEmailFieldRequiredness(TestCase):
    def test_email_field_requiredness(self):
        """Regression test for #1944.

        Previously a user without email address would not be able to add a comment."""

        # Arrange
        organization = Organization.objects.create(
            domain="example.org",
            fullname="Example Organisation",
        )
        CommentForm = django_comments.get_form()

        data = {
            "honeypot": "",
            "comment": "Content",
            "name": "Ron",  # required outside the request cycle
            **CommentForm(organization).generate_security_data(),
        }

        # Act
        form = CommentForm(organization, data)

        # Assert
        self.assertTrue(form.is_valid())

    def test_email_field_requiredness_POST(self):
        """Regression test for #1944.

        Previously a user without email address would not be able to add a comment.

        This test makes a POST request with comment data."""

        # Arrange
        person = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="rw",
            is_active=True,
            email="",
            data_privacy_agreement=True,
        )

        organization = Organization.objects.create(
            domain="example.org",
            fullname="Example Organisation",
        )

        CommentModel = django_comments.get_model()
        CommentForm = django_comments.get_form()
        data = {
            "honeypot": "",
            "comment": "Content",
            **CommentForm(organization).generate_security_data(),
        }

        # Act
        self.client.force_login(person)
        self.client.post(reverse("comments-post-comment"), data=data, follow=True)

        # Assert
        self.assertEqual(CommentModel.objects.for_model(organization).count(), 1)
