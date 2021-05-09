from django.test import TestCase
import django_comments

from workshops.models import Organization, Person


class TestEmailFieldRequiredness(TestCase):
    def test_email_field_requiredness(self):
        """Regression test for #1944.

        Previously a user without email address would not be able to add a comment."""
        # Arrange
        person = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="rw",
            is_active=True,
            email="",
        )
        person.set_password("testrwpassword")
        self.client.login(username="rw", password="testrwpassword")

        organization = Organization.objects.create(
            domain="example.org", fullname="Example Organisation"
        )
        CommentForm = django_comments.get_form()

        data = {
            "honeypot": "",
            "comment": "Content",
            "name": "Ron",
            **CommentForm(organization).generate_security_data(),
        }

        # Act
        form = CommentForm(organization, data)

        # Assert
        self.assertTrue(form.is_valid())
