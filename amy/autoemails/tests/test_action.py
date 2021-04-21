from datetime import timedelta

from django.contrib.sites.models import Site
from django.core import mail
from django.db.models import ProtectedError
from django.template.exceptions import TemplateSyntaxError
from django.test import TestCase, override_settings

from autoemails.actions import BaseAction
from autoemails.models import EmailTemplate, Trigger


@override_settings(AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS=None)
class TestAction(TestCase):
    def testLaunchTimestamp(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        a = BaseAction(trigger=Trigger(action="test-action", template=EmailTemplate()))
        a.launch_at = timedelta(days=10)

        self.assertEqual(a.get_launch_at(), timedelta(days=10))

    def testAdditionalContext(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        a = BaseAction(trigger=Trigger(action="test-action", template=EmailTemplate()))
        a.additional_context = dict(obj1="test1", obj2="test2", obj3=123)

        self.assertEqual(
            a.get_additional_context(), {"obj1": "test1", "obj2": "test2", "obj3": 123}
        )

    def testContext(self):
        # the trigger and email template below are totally fake
        # and shouldn't pass validation
        a = BaseAction(trigger=Trigger(action="test-action", template=EmailTemplate()))
        a.additional_context = dict(obj1="test1", obj2="test2", obj3=123)

        self.assertEqual(
            a._context(a.get_additional_context()),
            {
                "obj1": "test1",
                "obj2": "test2",
                "obj3": 123,
                "site": Site.objects.get_current(),
            },
        )

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

    def prepare_trigger(self):
        """Create a sample trigger using our sample template."""
        self.trigger = Trigger.objects.create(
            action="new-instructor",
            template=self.template,
        )

    def prepare_context(self):
        """Create a context dictionary that goes with trigger and email
        template created above."""
        self.objects = {
            "user": "Harry",
            "activities": ["Charms", "Potions", "Astronomy"],
            "admin": "Regional Coordinator",
            "reply_to": "regional@example.org",
        }
        return self.objects

    def testSuccessfulEmail(self):
        """Check ideal conditions for email building, with DB-based Trigger and
        EmailTemplate."""

        # 1. create Trigger and EmailTemplate
        self.prepare_template()
        self.prepare_trigger()

        # 2. create BaseAction, add context
        self.prepare_context()
        a = BaseAction(trigger=self.trigger, objects=self.objects)

        # 3. build email
        email = a._email()

        # 4. verify email
        self.assertEqual(email.to, [])
        self.assertEqual(email.cc, ["copy@example.org"])
        self.assertEqual(email.bcc, ["bcc@example.org"])
        self.assertEqual(email.reply_to, ["regional@example.org"])
        self.assertEqual(email.from_email, "test@address.com")
        self.assertEqual(email.subject, "Welcome to AMY")
        self.assertEqual(
            email.body,
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
            email.alternatives[0][0],
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
        self.assertEqual(len(mail.outbox), 0)  # no email sent yet

        # 5. send email!
        a()
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [])
        self.assertEqual(email.cc, ["copy@example.org"])
        self.assertEqual(email.bcc, ["bcc@example.org"])
        self.assertEqual(email.reply_to, ["regional@example.org"])
        self.assertEqual(email.from_email, "test@address.com")
        self.assertEqual(email.subject, "Welcome to AMY")

    def testEmailNotChangedTemplate(self):
        """Ensure email didn't change when template changed."""

        # 1. create Trigger and EmailTemplate
        self.prepare_template()
        self.prepare_trigger()

        # 2. create BaseAction, add context
        self.prepare_context()
        a = BaseAction(trigger=self.trigger, objects=self.objects)

        # 3. change something in template from DB
        tpl = EmailTemplate.objects.get(slug="sample-template")
        tpl.to_header = "{{ user_email }}"
        tpl.body_template = "Short template!!!"
        tpl.save()

        # 4. build email
        email = a._email()

        # 5. verify email
        self.assertEqual(email.to, [])
        self.assertEqual(email.cc, ["copy@example.org"])
        self.assertEqual(email.bcc, ["bcc@example.org"])
        self.assertEqual(email.reply_to, ["regional@example.org"])
        self.assertEqual(email.from_email, "test@address.com")
        self.assertEqual(email.subject, "Welcome to AMY")
        self.assertEqual(
            email.body,
            """Welcome, Harry!

It's a pleasure to have you here.


Here are some activities you can do:

* Charms

* Potions

* Astronomy



Sincerely,
Regional Coordinator""",
        )

    def testEmailChangedTrigger(self):
        """Check email building when trigger was changed."""

        # 1. create Trigger and EmailTemplate
        self.prepare_template()
        self.prepare_trigger()

        # 2. create BaseAction, add context
        self.prepare_context()
        a = BaseAction(trigger=self.trigger, objects=self.objects)
        self.assertEqual(a.trigger.action, "new-instructor")

        # 3. change something in template from DB
        trigg = Trigger.objects.get(action="new-instructor")
        trigg.action = "week-after-workshop-completion"
        trigg.save()

        # 4. build email
        a._email()

        # 5. verify
        self.assertEqual(a.trigger.action, "week-after-workshop-completion")

    def testEmailInvalidSyntax(self):
        """Check email building for invalid email."""

        # 1. create EmailTemplate
        self.prepare_template()

        # 2a. change template so that it has invalid syntax
        self.template.body_template = """Invalid syntax:
        * {{ unknown_variable }}
        * {{ user|unknown_filter }}
        * {% unknown_tag user %}
        """
        self.template.save()

        # 2b. create Trigger
        self.prepare_trigger()

        # 3. create BaseAction, add context
        self.prepare_context()
        a = BaseAction(trigger=self.trigger, objects=self.objects)

        # 4. build email - this will raise error
        with self.assertRaises(TemplateSyntaxError):
            a._email()

    def testEmailTemplateRemoved(self):
        """Remove referenced object (template) and ensure
        the email building fails correctly.

        It's impossible to remove the email template from DB, because it's
        guarded by Django/DB protection mechanisms."""
        # 1. create Trigger and EmailTemplate
        self.prepare_template()
        self.prepare_trigger()

        # 2. create BaseAction, add context
        self.prepare_context()
        BaseAction(trigger=self.trigger, objects=self.objects)

        # 3. remove trigger
        with self.assertRaises(ProtectedError):
            EmailTemplate.objects.filter(slug="sample-template").delete()

    def testTriggerRemoved(self):
        """Remove referenced trigger and ensure the email building fails
        correctly."""
        # 1. create Trigger and EmailTemplate
        self.prepare_template()
        self.prepare_trigger()

        # 2. create BaseAction, add context
        self.prepare_context()
        a = BaseAction(trigger=self.trigger, objects=self.objects)

        # 3. remove trigger
        Trigger.objects.filter(action="new-instructor").delete()

        # 4. build email
        with self.assertRaises(Trigger.DoesNotExist):
            a._email()

    @override_settings(AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS="test-address@example.org")
    def testOverrideSettings(self):
        """Check behavior with `AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS` setting.

        This setting is used to force a different outgoing address in the
        prepared email."""
        # 1. create Trigger and EmailTemplate
        self.prepare_template()
        self.prepare_trigger()
        self.template.to_header = "recipient@example.org"
        self.template.from_header = "sender@example.org"
        self.template.cc_header = "copy@example.org"
        self.template.bcc_header = "bcc@example.org"
        self.template.reply_to_header = "reply-to@example.org"

        # 2. create BaseAction, add context
        self.prepare_context()
        a = BaseAction(trigger=self.trigger, objects=self.objects)

        # 3. build email
        email = a._email()

        # 4. verify email - at this point the addresses stay the same, they are
        # not overridden yet
        self.assertEqual(email.to, ["recipient@example.org"])
        self.assertEqual(email.cc, ["copy@example.org"])
        self.assertEqual(email.bcc, ["bcc@example.org"])
        self.assertEqual(email.reply_to, ["reply-to@example.org"])
        self.assertEqual(email.from_email, "sender@example.org")

        # 5. verify no outgoing emails yet
        self.assertEqual(len(mail.outbox), 0)

        # 6. send email (by invoking action.__call__())
        a()

        # 7. check outgoing email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertEqual(email.to, ["test-address@example.org"])
        self.assertEqual(email.cc, [])
        self.assertEqual(email.bcc, [])
        self.assertEqual(email.reply_to, ["reply-to@example.org"])
        self.assertEqual(email.from_email, "sender@example.org")
