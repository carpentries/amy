from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.test import TestCase

from autoemails.models import EmailTemplate


class TestEmailTemplate(TestCase):
    def prepare_template(self):
        """Create a sample email template."""
        md = """Welcome, {{ user }}!

It's a pleasure to have you here.

{% if activities %}
Here are some activities you can do:
{% for item in activities %}
* {{ item }}
{% endfor %}
{% else %}
We haven't prepared you any activities yet.
{% endif %}

Sincerely,
{{ admin }}"""

        self.template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome to {{ site.name }}",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="{{ reply_to }}",
            body_template=md,
        )
        return self.template

    def prepare_context(self):
        """Create a context dictionary that goes with trigger and email
        template created above."""
        self.objects = {
            "user": "Harry",
            "activities": [
                "Charms",
                "Potions",
                "Astronomy",
            ],
            "admin": "Regional Coordinator",
            "reply_to": "regional@example.org",
            "site": Site.objects.get_current(),
        }
        return self.objects

    def test_rendering_template(self):
        template = (
            "Hello, {{ name }} {% if last_name %}{{ last_name }}"
            "{% else %}Smith{% endif %}"
        )

        data1 = {}
        # let's keep the hardcoded setting for missing variable in the template
        # system - just in case someone changes it unexpectedly
        expected_output1 = "Hello, XXX-unset-variable-XXX Smith"
        self.assertEqual(
            EmailTemplate.render_template(template, data1), expected_output1
        )

        data2 = {"name": "Harry"}
        expected_output2 = "Hello, Harry Smith"
        self.assertEqual(
            EmailTemplate.render_template(template, data2), expected_output2
        )

        data3 = {"name": "Harry", "last_name": "Potter"}
        expected_output3 = "Hello, Harry Potter"
        self.assertEqual(
            EmailTemplate.render_template(template, data3), expected_output3
        )

    def test_rendering_invalid_template(self):
        """Invalid filter or template tag should raise TemplateSyntaxError,
        whereas invalid variable should be changed to
        `XXX-unset-variable-XXX`."""
        template1 = "Hello, {{ name | nonexistentfilter }}!"
        data1 = dict(name="Harry")
        with self.assertRaises(TemplateSyntaxError):
            EmailTemplate.render_template(template1, data1)

        template2 = "Hello, {% invalidtag name %}!"
        data2 = dict(name="Harry")
        with self.assertRaises(TemplateSyntaxError):
            EmailTemplate.render_template(template2, data2)

        template3 = "Hello, {{ invalidname }}!"
        data3 = dict(name="Harry")
        self.assertEqual(
            EmailTemplate.render_template(template3, data3),
            "Hello, XXX-unset-variable-XXX!",
        )

    def test_reading_file_from_disk(self):
        """Non-default database engine backend shouldn't allow to read from
        disk."""
        # we're using a different backend than what's used for normal templates
        # because we don't want to allow users to render what they shouldn't
        template = "{% include 'base.html' %}"
        data = dict()
        with self.assertRaises(TemplateDoesNotExist):
            # with this test, we're confirming that `db_backend`, a default for
            # EmailTemplate, is unable to reach `base.html` file
            EmailTemplate.render_template(template, data)

        # this must work, because we're using Django-main template engine
        EmailTemplate.render_template(template, data, default_engine="django")

    def test_get_methods(self):
        tpl = self.prepare_template()
        ctx = self.prepare_context()

        self.assertEqual(tpl.get_subject(context=ctx), "Welcome to AMY")
        self.assertEqual(tpl.get_sender(context=ctx), "test@address.com")
        self.assertEqual(tpl.get_recipients(context=ctx), [])
        self.assertEqual(tpl.get_cc_recipients(context=ctx), ["copy@example.org"])
        self.assertEqual(tpl.get_bcc_recipients(context=ctx), ["bcc@example.org"])
        self.assertEqual(tpl.get_reply_to(context=ctx), ["regional@example.org"])
        body = tpl.get_body(context=ctx)
        self.assertEqual(len(body), 2)
        self.assertTrue(body.text)
        self.assertTrue(body.html)

    def test_rendering_markdown(self):
        tpl = self.prepare_template()
        ctx = self.prepare_context()
        body = tpl.get_body(context=ctx)
        self.assertEqual(
            body.text,
            """Welcome, Harry!

It's a pleasure to have you here.


Here are some activities you can do:

* Charms

* Potions

* Astronomy



Sincerely,
Regional Coordinator""",
        )

        self.assertEqual(
            body.html,
            """<p>Welcome, Harry!</p>
<p>It's a pleasure to have you here.</p>
<p>Here are some activities you can do:</p>
<ul>
<li>
<p>Charms</p>
</li>
<li>
<p>Potions</p>
</li>
<li>
<p>Astronomy</p>
</li>
</ul>
<p>Sincerely,
Regional Coordinator</p>""",
        )

    def test_syntax_check(self):
        """All fields should have Django syntax check validation enabled."""
        # case 1: wrong tag
        tpl1 = EmailTemplate(
            slug="test-template-1",
            subject="Wrong tag {% tag %}",
            to_header="Wrong tag {% tag %}",
            from_header="Wrong tag {% tag %}",
            cc_header="Wrong tag {% tag %}",
            bcc_header="Wrong tag {% tag %}",
            reply_to_header="Wrong tag {% tag %}",
            body_template="Wrong tag {% tag %}",
        )
        with self.assertRaises(ValidationError) as e:
            tpl1.clean()

        self.assertIn("subject", e.exception.error_dict)
        self.assertIn("to_header", e.exception.error_dict)
        self.assertIn("from_header", e.exception.error_dict)
        self.assertIn("cc_header", e.exception.error_dict)
        self.assertIn("bcc_header", e.exception.error_dict)
        self.assertIn("reply_to_header", e.exception.error_dict)
        self.assertIn("body_template", e.exception.error_dict)
        self.assertIn("Invalid", e.exception.message_dict["subject"][0])

        # case 2: missing opening or closing tags
        tpl2 = EmailTemplate(
            slug="test-template-2",
            subject="Missing {% url ",
            to_header="Missing {{ tag",
            from_header="Missing %}",
            cc_header="Missing }}",
            bcc_header="Missing {% tag }",
            reply_to_header="Missing {{ tag }",
            body_template="Missing { tag }}",
        )
        with self.assertRaises(ValidationError) as e:
            tpl2.clean()

        self.assertIn("subject", e.exception.error_dict)
        self.assertIn("to_header", e.exception.error_dict)
        self.assertIn("from_header", e.exception.error_dict)
        self.assertIn("cc_header", e.exception.error_dict)
        self.assertIn("bcc_header", e.exception.error_dict)
        self.assertIn("reply_to_header", e.exception.error_dict)
        self.assertIn("body_template", e.exception.error_dict)
        self.assertIn("Missing", e.exception.message_dict["subject"][0])

        # case 3: empty values should pass
        tpl3 = EmailTemplate(
            slug="test-template-3",
            subject="",
            to_header="",
            from_header="",
            cc_header="",
            bcc_header="",
            reply_to_header="",
            body_template="",
        )
        tpl3.clean()
