from datetime import date, datetime, timedelta

from django.test import TestCase

from autoemails.actions import (
    ProfileArchivalWarningAction,
    ProfileArchivalWarningRepeatedAction,
)
from autoemails.models import EmailReminder, EmailTemplate, RQJob, Trigger
from workshops.models import Person


class TestProfileArchivalWarningRepeatedAction(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.trigger = Trigger.objects.create(
            action="profile-archival-warning", template=EmailTemplate.objects.create()
        )
        self.action = ProfileArchivalWarningRepeatedAction(triggers=[self.trigger])

    def test_action(self) -> None:
        today = datetime.today()
        # Person with old profile
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = today - timedelta(years=4)
        p1.save()
        # person with old profile who is inactive
        p2 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            username="hgranger",
            email="hg@magic.uk",
            is_active=False,
        )
        p2.last_login = today - timedelta(years=4)
        p2.save()
        # person wiht current profile
        p3 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="rweasley",
            email="rw@magic.uk",
            is_active=True,
        )
        p3.last_login = today - timedelta(years=4)
        p3.save()

        self.action()
        rq_jobs = RQJob.objects.filter(trigger=self.action.triggers)
        self.assertCountEqual([job.recipients for job in rq_jobs], [p1.email])
        for job in rq_jobs:
            self.assertEqual(job.action_class, ProfileArchivalWarningAction)

    def test_user_logs_in_after_reminder(self) -> None:
        """
        User logged in
        """
        today = date.today()
        thirty_days_from_now = today + timedelta(days=30)

        # User hasn't logged in in a long time and a reminder email should be created
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = today - timedelta(years=4)
        p1.save()
        self.action()
        reminder = EmailReminder.objects.filter(
            remind_again_date=thirty_days_from_now, person=p1, trigger=self.trigger
        )
        self.assertEqual(len(reminder), 1)
        self.assertIsNone(reminder.archived_at)
        self.assertEqual(reminder.number_times_sent, 1)

        # user logs in and user's reminder email should be archived
        p1.last_login = today
        p1.save()
        self.action()
        reminder = EmailReminder.objects.filter(
            remind_again_date=thirty_days_from_now, person=p1, trigger=self.trigger
        )
        self.assertEqual(len(reminder), 1)
        self.assertIsNotNone(reminder.archived_at)
        self.assertEqual(reminder.number_times_sent, 1)

    def test_archive_email_reminder(self) -> None:
        """
        User logged in
        """
        today = date.today()
        thirty_days_from_now = today + timedelta(days=30)

        # User has received 3 reminders already and has not logged in
        # The Email reminder and person are archived
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = today - timedelta(years=4)
        p1.save()
        reminder = EmailReminder.objects.create(
            remind_again_date=thirty_days_from_now,
            person=p1,
            trigger=self.trigger,
            number_times_sent=3,
        )
        self.action()

        reminder = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminder), 1)
        self.assertIsNotNone(reminder.archived_at)
        self.assertIsNotNone(Person.objects.get(id=p1.id).archived_at)

    def test_resend_email_warning(self) -> None:
        today = date.today()
        thirty_days_from_now = today + timedelta(days=30)

        # User has received an email reminder already and has not logged in
        # The Email reminder is resent
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = today - timedelta(years=4)
        p1.save()
        reminder = EmailReminder.objects.create(
            remind_again_date=thirty_days_from_now,
            person=p1,
            trigger=self.trigger,
            number_times_sent=1,
        )
        self.action()

        reminder = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminder), 1)
        self.assertEqual(reminder.number_times_sent, 2)
        self.assertIsNone(reminder.archived_at)
        self.assertIsNone(Person.objects.get(id=p1.id).archived_at)
