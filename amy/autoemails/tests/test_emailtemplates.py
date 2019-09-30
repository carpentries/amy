from django.test import TestCase

from autoemails.models import EmailTemplate


class TestEmailTemplate(TestCase):
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
