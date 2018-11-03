import datetime
import json
from unittest.mock import patch

from django.http import QueryDict
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.test.base import APITestBase
from api.views import (
    TrainingRequests,
)

from workshops.models import (
    Person,
    Role,
    Event,
    Tag,
    Organization,
    Badge,
    KnowledgeDomain,
    TrainingRequest,
)


class TestListingTrainingRequests(APITestBase):
    view = TrainingRequests
    url = 'api:training-requests'
    maxDiff = None

    def setUp(self):
        # admin
        self.admin = Person.objects.create_superuser(
                username="admin", personal="Super", family="User",
                email="sudo@example.org", password='admin')
        self.admin.data_privacy_agreement = True
        self.admin.save()

        # some roles don't exist
        self.learner = Role.objects.create(name='learner',
                                           verbose_name='Learner')
        Role.objects.create(name='helper', verbose_name='Helper')

        # some tags don't exist either
        self.ttt = Tag.objects.create(name='TTT', details='Training')

        # first training request (pending)
        self.tr1 = TrainingRequest(
            state='p',
            person=None,
            group_name='GummiBears',
            personal='Zummi',
            middle='',
            family='Gummi-Glen',
            email='zummi@gummibears.com',
            github=None,
            occupation='',
            occupation_other='Magician',
            affiliation='Gummi-Glen',
            location='Forest',
            country='US',
            underresourced=True,
            domains_other='Magic',
            underrepresented='Yes',
            nonprofit_teaching_experience='None',
            previous_training='none',
            previous_training_other='',
            previous_training_explanation='I have no formal education',
            previous_experience='hours',
            previous_experience_other='',
            previous_experience_explanation='I taught other Gummies',
            programming_language_usage_frequency='not-much',
            teaching_frequency_expectation='monthly',
            teaching_frequency_expectation_other='',
            max_travelling_frequency='not-at-all',
            max_travelling_frequency_other='',
            reason='I hope to pass on the Gummi Wisdom one day, and to do that'
                   ' I must know how to do it efficiently.',
            comment='',
            training_completion_agreement=True,
            workshop_teaching_agreement=True,
            data_privacy_agreement=True,
            code_of_conduct_agreement=True,
        )
        self.tr1.save()
        self.tr1.domains.set(
            KnowledgeDomain.objects.filter(name__in=['Chemistry', 'Medicine'])
        )
        # no previous involvement
        self.tr1.previous_involvement.clear()

        # second training request (accepted)
        self.tr2 = TrainingRequest(
            state='a',
            person=self.admin,
            group_name='GummiBears',
            personal='Grammi',
            middle='',
            family='Gummi-Glen',
            email='grammi@gummibears.com',
            github=None,
            occupation='',
            occupation_other='Cook',
            affiliation='Gummi-Glen',
            location='Forest',
            country='US',
            underresourced=True,
            domains_other='Cooking',
            underrepresented='Yes',
            nonprofit_teaching_experience='None',
            previous_training='none',
            previous_training_other='',
            previous_training_explanation='I have no formal education',
            previous_experience='hours',
            previous_experience_other='',
            previous_experience_explanation='I taught other Gummies',
            programming_language_usage_frequency='not-much',
            teaching_frequency_expectation='monthly',
            teaching_frequency_expectation_other='',
            max_travelling_frequency='not-at-all',
            max_travelling_frequency_other='',
            reason='I need to pass on the Gummiberry juice recipe one day, and'
                   ' to do that I must know how to do it efficiently.',
            comment='',
            training_completion_agreement=True,
            workshop_teaching_agreement=True,
            data_privacy_agreement=True,
            code_of_conduct_agreement=True,
        )
        self.tr2.save()
        self.tr2.domains.set(
            KnowledgeDomain.objects.filter(name__in=['Chemistry'])
        )
        self.tr2.previous_involvement.set(
            Role.objects.filter(name__in=['learner', 'helper'])
        )

        # add TTT event self.admin was matched to
        self.ttt_event = Event(
            slug='2018-07-12-TTT-event',
            host=Organization.objects.first(),
        )
        self.ttt_event.save()
        self.ttt_event.tags.set(Tag.objects.filter(name='TTT'))
        self.admin.task_set.create(role=self.learner, event=self.ttt_event)

        # add some badges
        self.admin.award_set.create(
            badge=Badge.objects.get(name='swc-instructor'),
            awarded=datetime.date(2018, 7, 12)
        )
        self.admin.award_set.create(
            badge=Badge.objects.get(name='dc-instructor'),
            awarded=datetime.date(2018, 7, 12)
        )

        current_tz = timezone.get_current_timezone()

        # prepare expecting dataset
        self.expecting = [
            {
                'created_at':
                    self.tr1.created_at.astimezone(current_tz).isoformat(),
                'last_updated_at':
                    self.tr1.last_updated_at.astimezone(current_tz).isoformat(),
                'state': 'Pending',
                'person': None,
                'person_id': None,
                'awards': '',
                'training_tasks': '',
                'group_name': 'GummiBears',
                'personal': 'Zummi',
                'middle': '',
                'family': 'Gummi-Glen',
                'email': 'zummi@gummibears.com',
                'github': None,
                'underrepresented': 'Yes',
                'occupation': '',
                'occupation_other': 'Magician',
                'affiliation': 'Gummi-Glen',
                'location': 'Forest',
                'country': 'US',
                'underresourced': True,
                'domains': 'Chemistry, Medicine',
                'domains_other': 'Magic',
                'nonprofit_teaching_experience': 'None',
                'previous_involvement': '',
                'previous_training': 'None',
                'previous_training_other': '',
                'previous_training_explanation': 'I have no formal education',
                'previous_experience': 'A few hours',
                'previous_experience_other': '',
                'previous_experience_explanation': 'I taught other Gummies',
                'programming_language_usage_frequency':
                    'Never or almost never',
                'teaching_frequency_expectation': 'Several times a year',
                'teaching_frequency_expectation_other': '',
                'max_travelling_frequency': 'Not at all',
                'max_travelling_frequency_other': '',
                'reason':
                    'I hope to pass on the Gummi Wisdom one day, and to do '
                    'that I must know how to do it efficiently.',
                'comment': '',
                'training_completion_agreement': True,
                'workshop_teaching_agreement': True,
                'data_privacy_agreement': True,
                'code_of_conduct_agreement': True,
            },
            {
                'created_at':
                    self.tr2.created_at.astimezone(current_tz).isoformat(),
                'last_updated_at':
                    self.tr2.last_updated_at.astimezone(current_tz).isoformat(),
                'state': 'Accepted',
                'person': 'Super User',
                'person_id': self.admin.pk,
                'awards': 'swc-instructor 2018-07-12, '
                          'dc-instructor 2018-07-12',
                'training_tasks': '2018-07-12-TTT-event',
                'group_name': 'GummiBears',
                'personal': 'Grammi',
                'middle': '',
                'family': 'Gummi-Glen',
                'email': 'grammi@gummibears.com',
                'github': None,
                'underrepresented': 'Yes',
                'occupation': '',
                'occupation_other': 'Cook',
                'affiliation': 'Gummi-Glen',
                'location': 'Forest',
                'country': 'US',
                'underresourced': True,
                'domains': 'Chemistry',
                'domains_other': 'Cooking',
                'nonprofit_teaching_experience': 'None',
                'previous_involvement': 'learner, helper',
                'previous_training': 'None',
                'previous_training_other': '',
                'previous_training_explanation': 'I have no formal education',
                'previous_experience': 'A few hours',
                'previous_experience_other': '',
                'previous_experience_explanation':
                    'I taught other Gummies',
                'programming_language_usage_frequency':
                    'Never or almost never',
                'teaching_frequency_expectation': 'Several times a year',
                'teaching_frequency_expectation_other': '',
                'max_travelling_frequency': 'Not at all',
                'max_travelling_frequency_other': '',
                'reason':
                    'I need to pass on the Gummiberry juice recipe one day,'
                    ' and to do that I must know how to do it efficiently.',
                'comment': '',
                'training_completion_agreement': True,
                'workshop_teaching_agreement': True,
                'data_privacy_agreement': True,
                'code_of_conduct_agreement': True,
            },
        ]

    @patch.object(TrainingRequests, 'request', query_params=QueryDict(),
                  create=True)
    def test_serialization(self, mock_request):
        # we're mocking a request here because it's not possible to create
        # a fake request context for the view
        serializer_class = self.view().get_serializer_class()
        response = serializer_class(self.view().get_queryset(), many=True)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0], self.expecting[0])
        self.assertEqual(response.data[1], self.expecting[1])

    def test_CSV_renderer(self):
        """Test columns order and labels in the resulting CSV file."""
        url = reverse(self.url)

        # get CSV-formatted output
        self.client.login(username='admin', password='admin')
        response = self.client.get(url, {'format': 'csv'})
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        firstline = content.splitlines()[0]
        expected_firstline = (
            'Created at,Last updated at,State,Matched Trainee,'
            'Matched Trainee ID,Badges,Training Tasks,Group Name,'
            'Personal,Middle,Family,Email,GitHub username,'
            'Underrepresented (reason),Occupation,Occupation (other),'
            'Affiliation,Location,Country,Underresourced institution,'
            'Expertise areas,Expertise areas (other),'
            'Non-profit teaching experience,Previous Involvement,'
            'Previous Training in Teaching,Previous Training (other),'
            'Previous Training (explanation),Previous Experience in Teaching,'
            'Previous Experience (other),Previous Experience (explanation),'
            'Programming Language Usage,Teaching Frequency Expectation,'
            'Teaching Frequency Expectation (other),Max Travelling Frequency,'
            'Max Travelling Frequency (other),Reason for undertaking training,'
            'Comment,Training completion agreement (yes/no),'
            'Workshop teaching agreement (yes/no),'
            'Data privacy agreement (yes/no),'
            'Code of Conduct agreement (yes/no)'
        )

        self.assertEqual(firstline, expected_firstline)

    @patch.object(TrainingRequests, 'request', query_params=QueryDict(),
                  create=True)
    def test_M2M_columns(self, mock_request):
        """Some columns are M2M fields, but should be displayed as a string,
        not array /list/."""
        # the same mocking as in test_serialization
        serializer_class = self.view().get_serializer_class()
        response = serializer_class(self.view().get_queryset(), many=True)
        self.assertEqual(len(response.data), 2)

        self.assertEqual(response.data[0]['domains'], 'Chemistry, Medicine')
        self.assertEqual(response.data[1]['previous_involvement'],
                         'learner, helper')

    def test_selected_ids(self):
        """Test if filtering by IDs works properly."""
        url = reverse(self.url)

        self.client.login(username='admin', password='admin')
        response = self.client.get(url, {'ids': '{}'.format(self.tr2.pk)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        json = response.json()
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0], self.expecting[1])
