from django.contrib.sites.models import Site
from django.template.exceptions import TemplateSyntaxError
from django.test import TestCase

from autoemails.models import EmailTemplate


class TestEmailTemplate(TestCase):
    def prepare_template(self):
        """Create a sample email template."""
        html = """<p>Welcome, {{ user }}!</p>
<p>It's a pleasure to have you here.</p>
{% if activities %}
<p>Here are some activities you can do:</p>
<ul>
    {% for item in activities %}
    <li>{{ item }}</li>
    {% endfor %}
</ul>
{% else %}
<p>We haven't prepared you any activities yet.</p>
{% endif %}
<p>Sincerely,<br>{{ admin }}</p>"""
        text = """Welcome, {{ user }}!

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
            slug='sample-template',
            subject='Welcome to {{ site.name }}',
            to_header='',
            from_header='test@address.com',
            cc_header='copy@example.org',
            bcc_header='bcc@example.org',
            reply_to_header='{{ reply_to }}',
            html_template=html,
            text_template=text,
        )
        return self.template

    def prepare_context(self):
        """Create a context dictionary that goes with trigger and email
        template created above."""
        self.objects = {
            'user': 'Harry',
            'activities': [
                'Charms',
                'Potions',
                'Astronomy',
            ],
            'admin': 'Regional Coordinator',
            'reply_to': 'regional@example.org',
            'site': Site.objects.get_current(),
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
        self.assertEqual(EmailTemplate.render_template(template, data1),
                         expected_output1)

        data2 = {'name': 'Harry'}
        expected_output2 = "Hello, Harry Smith"
        self.assertEqual(EmailTemplate.render_template(template, data2),
                         expected_output2)

        data3 = {'name': 'Harry', 'last_name': 'Potter'}
        expected_output3 = "Hello, Harry Potter"
        self.assertEqual(EmailTemplate.render_template(template, data3),
                         expected_output3)
    
    def test_rendering_invalid_template(self):
        """Invalid filter or template tag should raise TemplateSyntaxError,
        whereas invalid variable should be changed to
        `XXX-unset-variable-XXX`."""
        template1 = "Hello, {{ name | nonexistentfilter }}!"
        data1 = dict(name='Harry')
        with self.assertRaises(TemplateSyntaxError):
            EmailTemplate.render_template(template1, data1)

        template2 = "Hello, {% invalidtag name %}!"
        data2 = dict(name='Harry')
        with self.assertRaises(TemplateSyntaxError):
            EmailTemplate.render_template(template2, data2)

        template3 = "Hello, {{ invalidname }}!"
        data3 = dict(name='Harry')
        self.assertEqual(EmailTemplate.render_template(template3, data3),
                         "Hello, XXX-unset-variable-XXX!")

    def test_get_methods(self):
        tpl = self.prepare_template()
        ctx = self.prepare_context()

        self.assertEqual(tpl.get_subject(context=ctx), 'Welcome to AMY')
        self.assertEqual(tpl.get_sender(context=ctx), 'test@address.com')
        self.assertEqual(tpl.get_recipients(context=ctx), [])
        self.assertEqual(tpl.get_cc_recipients(context=ctx),
                         ['copy@example.org'])
        self.assertEqual(tpl.get_bcc_recipients(context=ctx),
                         ['bcc@example.org'])
        self.assertEqual(tpl.get_reply_to(context=ctx),
                         ['regional@example.org'])
