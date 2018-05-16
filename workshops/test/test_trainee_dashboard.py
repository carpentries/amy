from datetime import datetime

from django.urls import reverse

from workshops.models import Person, Award, Badge, TrainingProgress, \
    TrainingRequirement
from workshops.test import TestBase


class TestTraineeDashboard(TestBase):
    """Tests for trainee dashboard."""
    def setUp(self):
        self.user = Person.objects.create_user(
            username='user', personal='', family='',
            email='user@example.org', password='pass')
        self.client.login(username='user', password='pass')

    def test_dashboard_loads(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self.assertIn("Log out", content)
        self.assertIn("Update your profile", content)


class TestInstructorStatus(TestBase):
    """Test that trainee dashboard displays information about awarded SWC/DC
    Instructor badges."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.swc_instructor = Badge.objects.get(name='swc-instructor')
        self.dc_instructor = Badge.objects.get(name='dc-instructor')

    def test_swc_instructor_and_dc_instructor(self):
        """When the trainee is awarded both Carpentry Instructor badge,
        we want to display that info in the dashboard."""

        Award.objects.create(person=self.admin, badge=self.swc_instructor,
                             awarded=datetime(2016, 6, 1, 15, 00))
        Award.objects.create(person=self.admin, badge=self.dc_instructor,
                             awarded=datetime(2016, 6, 1, 15, 00))
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Congratulations, you\'re certified both '
                                'Software Carpentry and Data Carpentry '
                                'Instructor!')

    def test_swc_instructor(self):
        Award.objects.create(person=self.admin, badge=self.swc_instructor,
                             awarded=datetime(2016, 6, 1, 15, 00))
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Congratulations, you\'re certified '
                                'Software Carpentry Instructor!')

    def test_dc_instructor(self):
        Award.objects.create(person=self.admin, badge=self.dc_instructor,
                             awarded=datetime(2016, 6, 1, 15, 00))
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Congratulations, you\'re certified '
                                'Data Carpentry Instructor!')

    def test_neither_swc_nor_dc_instructor(self):
        """Check that we don't display that the trainee is an instructor if
        they don't have appropriate badge."""
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertNotContains(rv, 'Congratulations, you\'re certified both '
                                   'Software Carpentry and Data Carpentry '
                                   'Instructor!')
        self.assertNotContains(rv, 'Congratulations, you\'re certified '
                                   'Software Carpentry Instructor!')
        self.assertNotContains(rv, 'Congratulations, you\'re certified '
                                   'Data Carpentry Instructor!')

    def test_eligible_but_not_awarded(self):
        """Test what is dispslayed when a trainee is eligible to be certified
        as an SWC/DC Instructor, but doesn't have appropriate badge awarded
        yet."""
        requirements = ['Training', 'SWC Homework', 'DC Homework',
                        'Discussion', 'SWC Demo', 'DC Demo']
        for requirement in requirements:
            TrainingProgress.objects.create(
                trainee=self.admin,
                requirement=TrainingRequirement.objects.get(name=requirement))

        admin = Person.objects.annotate_with_instructor_eligibility() \
                              .get(username='admin')
        assert admin.get_missing_swc_instructor_requirements() == []
        assert admin.get_missing_dc_instructor_requirements() == []

        rv = self.client.get(reverse('trainee-dashboard'))

        self.assertNotContains(rv, 'Congratulations, you\'re certified both '
                                   'Software Carpentry and Data Carpentry '
                                   'Instructor!')
        self.assertNotContains(rv, 'Congratulations, you\'re certified '
                                   'Software Carpentry Instructor!')
        self.assertNotContains(rv, 'Congratulations, you\'re certified '
                                   'Data Carpentry Instructor!')


class TestInstructorTrainingStatus(TestBase):
    """Test that trainee dashboard displays status of passing Instructor
    Training."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.training = TrainingRequirement.objects.get(name='Training')

    def test_training_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Training passed')

    def test_training_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Training not passed yet')

    def test_last_training_discarded_but_another_is_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Training passed')

    def test_training_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.training, state='f')
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Training not passed yet')

    def test_training_not_finished(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Training not passed yet')


class TestSWCHomeworkStatus(TestBase):
    """Test that trainee dashboard displays status of passing SWC Homework.
    Test that SWC homework submission form works."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.homework = TrainingRequirement.objects.get(name='SWC Homework')

    def test_homework_not_submitted(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Homework not submitted yet')

    def test_homework_waiting_to_be_evaluated(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework, state='n')
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Homework not evaluated yet')

    def test_homework_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Homework accepted')

    def test_homework_not_accepted_when_homework_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Homework not submitted yet')

    def test_homework_is_accepted_when_last_homework_is_discarded_but_other_one_is_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Homework accepted')

    def test_submission_form(self):
        data = {
            'url': 'http://example.com',
            'swc-submit': '',
        }
        rv = self.client.post(reverse('trainee-dashboard'), data, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'trainee-dashboard')
        self.assertContains(rv, 'Your homework submission will be evaluated '
                                'soon.')
        got = list(TrainingProgress.objects.values_list(
            'state', 'trainee', 'url', 'requirement'))
        expected = [(
            'n',
            self.admin.pk,
            'http://example.com',
            TrainingRequirement.objects.get(name='SWC Homework').pk,
        )]
        self.assertEqual(got, expected)


class TestDCHomeworkStatus(TestBase):
    """Test that trainee dashboard displays status of passing DC Homework.
    Test that DC homework submission form works."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.homework = TrainingRequirement.objects.get(name='DC Homework')

    def test_homework_not_submitted(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Homework not submitted yet')

    def test_homework_waiting_to_be_evaluated(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework, state='n')
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Homework not evaluated yet')

    def test_homework_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Homework accepted')

    def test_homework_not_accepted_when_homework_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Homework not submitted yet')

    def test_homework_is_accepted_when_last_homework_is_discarded_but_other_one_is_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.homework, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Homework accepted')

    def test_submission_form(self):
        data = {
            'url': 'http://example.com',
            'dc-submit': '',
        }
        rv = self.client.post(reverse('trainee-dashboard'), data, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'trainee-dashboard')
        self.assertContains(rv, 'Your homework submission will be evaluated '
                                'soon.')
        got = list(TrainingProgress.objects.values_list(
            'state', 'trainee', 'url', 'requirement'))
        expected = [(
            'n',
            self.admin.pk,
            'http://example.com',
            TrainingRequirement.objects.get(name='DC Homework').pk,
        )]
        self.assertEqual(got, expected)


class TestDiscussionSessionStatus(TestBase):
    """Test that trainee dashboard displays status of passing Discussion
    Session. Test whether we display instructions for registering for a
    session. """

    def setUp(self):
        self._setUpUsersAndLogin()
        self.discussion = TrainingRequirement.objects.get(name='Discussion')

    def test_session_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Discussion Session passed')

    def test_session_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Discussion Session not passed yet')

    def test_last_session_discarded_but_another_is_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Discussion Session passed')

    def test_session_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.discussion, state='f')
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Discussion Session not passed yet')

    def test_no_participation_in_a_session_yet(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'Discussion Session not passed yet')


class TestDemoSessionStatus(TestBase):
    """Test that trainee dashboard displays status of passing SWC/DC Demo
    Session. Test whether we display instructions for registering for a
    session."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self.swc_demo = TrainingRequirement.objects.get(name='SWC Demo')
        self.dc_demo = TrainingRequirement.objects.get(name='DC Demo')

    def test_swc_session_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.swc_demo)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Demo Session passed')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_swc_session_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.swc_demo, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Demo Session not passed yet')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_swc_last_session_discarded_but_another_is_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.swc_demo)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.swc_demo, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Demo Session passed')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_swc_session_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.swc_demo, state='f')
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Demo Session not passed yet')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_no_participation_in_a_swc_session_yet(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Demo Session not passed yet')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_dc_session_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.dc_demo)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Demo Session passed')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_dc_session_passed_but_discarded(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.dc_demo, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Demo Session not passed yet')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_dc_last_session_discarded_but_another_is_passed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.dc_demo)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.dc_demo, discarded=True)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Demo Session passed')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_dc_session_failed(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.dc_demo, state='f')
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Demo Session not passed yet')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_no_participation_in_a_dc_session_yet(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'DC Demo Session not passed yet')
        self.assertContains(rv, 'Register for Demo Session on')

    def test_no_registration_instruction_when_trainee_passed_both_swc_and_dc_sessions(self):
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.swc_demo)
        TrainingProgress.objects.create(
            trainee=self.admin, requirement=self.dc_demo)
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertContains(rv, 'SWC Demo Session passed')
        self.assertContains(rv, 'DC Demo Session passed')
        self.assertNotContains(rv, 'Register for Demo Session on')
