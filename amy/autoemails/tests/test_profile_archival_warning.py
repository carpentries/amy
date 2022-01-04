from datetime import timedelta
from typing import Type

from django.test import TestCase
from django.utils import timezone

from autoemails.actions import (
    BaseRepeatedAction,
    ProfileArchivalWarningConsentsAction,
    ProfileArchivalWarningConsentsRepeatedAction,
    ProfileArchivalWarningInactivityAction,
    ProfileArchivalWarningInactivityRepeatedAction,
)
from autoemails.models import EmailReminder, EmailTemplate, RQJob, Trigger
from workshops.models import Person


class BaseProfileArchivalWarningRepeatedActionTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.trigger = Trigger.objects.create(
            action=ProfileArchivalWarningInactivityRepeatedAction.ACTION_NAME,
            template=EmailTemplate.objects.create(),
        )
        self.action = ProfileArchivalWarningInactivityRepeatedAction(
            trigger=self.trigger
        )
        self.today = timezone.now()
        self.thirty_days_from_now = self.today + timedelta(days=30)
        self.four_years_ago = self.today - timedelta(days=365 * 4)

    def get_repeated_action(self) -> Type[BaseRepeatedAction]:
        raise NotImplementedError

    def assert_reminder(
        self,
        reminder: EmailReminder,
        expected_person: Person,
        number_of_times_sent: int = 1,
        is_archived: bool = False,
    ) -> None:
        """
        Asserts that the reminder's remind again date
        has been updated to 30 days from today
        """
        self.assertEqual(
            reminder.remind_again_date.year, self.thirty_days_from_now.year
        )
        self.assertEqual(
            reminder.remind_again_date.month, self.thirty_days_from_now.month
        )
        self.assertEqual(reminder.remind_again_date.day, self.thirty_days_from_now.day)
        if is_archived:
            self.assertIsNotNone(reminder.archived_at)
        else:
            self.assertIsNone(reminder.archived_at)
        self.assertEqual(reminder.number_times_sent, number_of_times_sent)
        self.assertEqual(reminder.person, expected_person)
        self.assertEqual(reminder.trigger, self.trigger)

    def assert_person_not_archived(self, person: Person) -> None:
        self.assertTrue(person.is_active)
        self.assertIsNone(person.archived_at)

    def assert_person_archived(self, person: Person) -> None:
        self.assertIsNotNone(person.archived_at)
        self.assertFalse(person.is_active)


class TestProfileArchivalWarningInactivityRepeatedAction(
    BaseProfileArchivalWarningRepeatedActionTest
):
    def get_repeated_action(self) -> Type[BaseRepeatedAction]:
        return ProfileArchivalWarningInactivityRepeatedAction

    def test_send_emails_to_users(self) -> None:
        """
        Tests that the emails that should be sent out are given the users.
        An email is sent if:
        - Person has not logged in a long time
        - Person is active
        """
        # Person with old profile that is still active
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = self.four_years_ago
        p1.save()
        # person with old profile who is inactive
        p2 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            username="hgranger",
            email="hg@magic.uk",
            is_active=False,
        )
        p2.last_login = self.four_years_ago
        p2.save()
        # person with current profile
        Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="rweasley",
            email="rw@magic.uk",
            is_active=True,
        )

        # Only person 1 is sent an email
        self.action()
        rq_jobs = RQJob.objects.filter(trigger=self.action.trigger)
        self.assertCountEqual([job.recipients for job in rq_jobs], [p1.email])
        for job in rq_jobs:
            self.assertEqual(
                job.action_name, ProfileArchivalWarningInactivityAction.__name__
            )
            self.assertIsNone(job.interval)
            self.assertIsNone(job.result_ttl)
        # person 1 should also have an email reminder in the database
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1)
        self.assert_person_not_archived(p1)

    def test_user_logs_in_after_reminder(self) -> None:
        """
        User logged in after the reminder.
        The user should not be archived in subsequent checks
        and the email reminder should be archived.
        """
        # User hasn't logged in in a long time and a reminder email should be created
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = self.four_years_ago
        p1.save()
        self.action()
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        # reminder created to remind the user again in 30 days
        self.assert_reminder(reminders[0], p1)
        self.assert_person_not_archived(p1)

        # user logs in and user's reminder email should be archived
        p1.last_login = self.today
        p1.save()
        self.action()
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)

        # reminder was archived with no changes
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1, is_archived=True)
        self.assert_person_not_archived(p1)

    def test_archive_email_reminder(self) -> None:
        """
        User has not logged in after three email reminders.
        The user is archived and so is the email reminder.
        """
        # User has received 3 reminders already and has not logged in
        # The Email reminder and person are archived
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = self.four_years_ago
        p1.save()
        EmailReminder.objects.create(
            remind_again_date=self.thirty_days_from_now,
            person=p1,
            trigger=self.trigger,
            number_times_sent=3,
        )
        self.action()
        p1.refresh_from_db()

        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1, number_of_times_sent=3, is_archived=True)
        self.assert_person_archived(p1)

    def test_resend_email_warning(self) -> None:
        """
        User has received an email reminder already and has not logged in
        another email reminder is sent and the reminder is updated in the database.
        """
        today = timezone.now()

        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = today - timedelta(days=365 * 4)
        p1.save()
        EmailReminder.objects.create(
            remind_again_date=self.thirty_days_from_now,
            person=p1,
            trigger=self.trigger,
            number_times_sent=1,
        )
        self.action()
        p1.refresh_from_db()

        # another email reminder is sent and no changes are made to the user
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1, number_of_times_sent=2)
        self.assert_person_not_archived(p1)


class TestProfileArchivalWarningConsentsRepeatedAction(
    BaseProfileArchivalWarningRepeatedActionTest
):
    def get_repeated_action(self) -> Type[BaseRepeatedAction]:
        return ProfileArchivalWarningConsentsRepeatedAction

    def test_send_emails_to_users(self) -> None:
        """
        Tests that the emails are sent to the correct users.
        An email is sent if:
        - Person is active, is not archived, and has missing consents.
        """
        # Person with missing consents that is still active
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )

        # person with missing consents who is archived
        Person.objects.create(
            personal="Hermione",
            family="Granger",
            username="hgranger",
            email="hg@magic.uk",
            is_active=False,
        )
        # person with all consents and current profile
        Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="rweasley",
            email="rw@magic.uk",
            is_active=True,
        )

        # Only person 1 is sent an email
        self.action()
        rq_jobs = RQJob.objects.filter(trigger=self.action.trigger)
        self.assertCountEqual([job.recipients for job in rq_jobs], [p1.email])
        for job in rq_jobs:
            self.assertEqual(
                job.action_name, ProfileArchivalWarningConsentsAction.__name__
            )
            self.assertIsNone(job.interval)
            self.assertIsNone(job.result_ttl)
        # person 1 should also have an email reminder in the database
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1)
        self.assert_person_not_archived(p1)

    def test_user_logs_in_after_reminder(self) -> None:
        """
        User logged in after the reminder.
        The user should not be archived in subsequent checks
        and the email reminder should be archived.
        """
        # User hasn't logged in in a long time and a reminder email should be created
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = self.four_years_ago
        p1.save()
        self.action()
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        # reminder created to remind the user again in 30 days
        self.assert_reminder(reminders[0], p1)
        self.assert_person_not_archived(p1)

        # user logs in and user's reminder email should be archived
        p1.last_login = self.today
        p1.save()
        self.action()
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)

        # reminder was archived with no changes
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1, is_archived=True)
        self.assert_person_not_archived(p1)

    def test_archive_email_reminder(self) -> None:
        """
        User has not logged in after three email reminders.
        The user is archived and so is the email reminder.
        """
        # User has received 3 reminders already and has not logged in
        # The Email reminder and person are archived
        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = self.four_years_ago
        p1.save()
        EmailReminder.objects.create(
            remind_again_date=self.thirty_days_from_now,
            person=p1,
            trigger=self.trigger,
            number_times_sent=3,
        )
        self.action()
        p1.refresh_from_db()

        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1, number_of_times_sent=3, is_archived=True)
        self.assert_person_archived(p1)

    def test_resend_email_warning(self) -> None:
        """
        User has received an email reminder already and has not logged in
        another email reminder is sent and the reminder is updated in the database.
        """
        today = timezone.now()

        p1 = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk", is_active=True
        )
        p1.last_login = today - timedelta(days=365 * 4)
        p1.save()
        EmailReminder.objects.create(
            remind_again_date=self.thirty_days_from_now,
            person=p1,
            trigger=self.trigger,
            number_times_sent=1,
        )
        self.action()
        p1.refresh_from_db()

        # another email reminder is sent and no changes are made to the user
        reminders = EmailReminder.objects.filter(person=p1, trigger=self.trigger)
        self.assertEqual(len(reminders), 1)
        self.assert_reminder(reminders[0], p1, number_of_times_sent=2)
        self.assert_person_not_archived(p1)
