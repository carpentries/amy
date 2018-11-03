# coding: utf-8
import cgi
import datetime
from io import StringIO

from django.contrib.sessions.serializers import JSONSerializer
from django.urls import reverse

from workshops.models import Person, TrainingRequest
from workshops.util import (
    upload_trainingrequest_manual_score_csv,
    clean_upload_trainingrequest_manual_score,
    update_manual_score,
)

from workshops.tests.base import TestBase
from workshops.tests.test_training_request import create_training_request


class UploadTrainingRequestManualScoreCSVTestCase(TestBase):
    def compute_from_string(self, csv_str):
        """Wrap string into IO buffer & parse."""
        csv_buf = StringIO(csv_str)
        return upload_trainingrequest_manual_score_csv(csv_buf)

    def test_basic_parsing(self):
        """Test if perfectly correct CSV loads... correctly."""
        csv = """request_id,score_manual,score_notes
1,123,"This person exceeded at receiving big manual score."
2,-321,They did bad at our survey"""
        data = self.compute_from_string(csv)

        # correct length
        self.assertEqual(len(data), 2)

        # ensure data has correct format
        self.assertEqual(
            set(data[0].keys()),
            set(TrainingRequest.MANUAL_SCORE_UPLOAD_FIELDS + ("errors", ))
        )

    def test_csv_without_required_field(self):
        """Only fields from TrainingRequest.MANUAL_SCORE_UPLOAD_FIELDS are
        taken into consideration, and they all should be present."""
        bad_csv = """request_id,completely_different_field,score_notes
1,123,"This person exceeded at receiving big manual score."
2,-321,They did bad at our survey"""
        data = self.compute_from_string(bad_csv)
        self.assertTrue(data[0]['score_manual'] is None)
        self.assertTrue(data[1]['score_manual'] is None)

    def test_csv_with_empty_lines(self):
        csv = """request_id,score_manual,score_notes
1,123,"This person exceeded at receiving big manual score."
,,"""
        data = self.compute_from_string(csv)
        self.assertEqual(len(data), 1)

    def test_empty_field(self):
        """Ensure blank fields don't reorder other fields."""
        csv = """request_id,score_manual,score_notes
1,,'This person exceeded at receiving big manual score.'"""
        data = self.compute_from_string(csv)
        entry = data[0]
        self.assertEqual(entry['score_manual'], '')

    def test_serializability_of_parsed(self):
        csv = """request_id,score_manual,score_notes
1,123,"This person exceeded at receiving big manual score."
2,-321,They did bad at our survey"""
        data = self.compute_from_string(csv)

        try:
            serializer = JSONSerializer()
            serializer.dumps(data)
        except TypeError:
            self.fail('Dumping manual scores for Training Requests into JSON '
                      'unexpectedly failed!')

    def test_malformed_CSV_with_proper_header_row(self):
        csv = """request_id,score_manual,score_notes
This is a malformed CSV"""
        data = self.compute_from_string(csv)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['request_id'], 'This is a malformed CSV')
        self.assertEqual(data[0]['score_manual'], None)
        self.assertEqual(data[0]['score_notes'], None)


class CSVBulkUploadTestBase(TestBase):
    """Provide auxiliary methods used in descendant TestCases."""

    def setUp(self):
        """Prepare some existing Training Requests."""
        self.tr1 = create_training_request(state='p', person=None)
        self.tr1.score_manual = 10
        self.tr1.score_notes = "This request received positive manual score"
        self.tr1.save()

        self.tr2 = create_training_request(state='p', person=None)
        self.tr2.score_manual = -10
        self.tr2.score_notes = "This request received negative manual score"
        self.tr2.save()

        self.tr3 = create_training_request(state='p', person=None)
        self.tr3.score_manual = 0
        self.tr3.score_notes = "This request was manually scored to zero"
        self.tr3.save()

        self.tr4 = create_training_request(state='p', person=None)
        self.tr4.score_manual = None
        self.tr4.score_notes = "This request hasn't been scored manually"
        self.tr4.save()

    def make_csv_data(self):
        return """request_id,score_manual,score_notes
{},-10,"This person did bad."
{},0,"This person did neutral."
{},10,"This person exceeded ."
{},0,This person did OK.""".format(
            self.tr1.pk, self.tr2.pk, self.tr3.pk, self.tr4.pk
        )

    def make_data(self):
        csv_str = self.make_csv_data()
        data = upload_trainingrequest_manual_score_csv(StringIO(csv_str))
        return data


class CleanUploadTrainingRequestManualScore(CSVBulkUploadTestBase):
    """
    Testing scenarios:
    * everything is good
    * missing request ID, score manual, or score notes
    * wrong format for request ID or score manual
    * request ID not matching any existing requests
    """

    def test_verify_with_good_data(self):
        data = self.make_data()
        has_errors, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertFalse(has_errors)
        # empty list evaluates to False
        self.assertFalse(cleaned[0]['errors'])
        self.assertFalse(cleaned[1]['errors'])
        self.assertFalse(cleaned[2]['errors'])
        self.assertFalse(cleaned[3]['errors'])

    def test_missing_request_ID(self):
        data = self.make_data()
        data[1]['request_id'] = ''

        has_errors, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertTrue(has_errors)
        self.assertFalse(cleaned[0]['errors'])
        self.assertTrue(cleaned[1]['errors'])
        self.assertFalse(cleaned[2]['errors'])
        self.assertFalse(cleaned[3]['errors'])

        self.assertIn('Request ID is missing.', cleaned[1]['errors'])

    def test_missing_score_manual(self):
        data = self.make_data()
        data[1]['score_manual'] = ''

        has_errors, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertTrue(has_errors)
        self.assertFalse(cleaned[0]['errors'])
        self.assertTrue(cleaned[1]['errors'])
        self.assertFalse(cleaned[2]['errors'])
        self.assertFalse(cleaned[3]['errors'])

        self.assertIn('Manual score is missing.', cleaned[1]['errors'])

    def test_missing_score_notes(self):
        """Missing notes should not trigger any errors."""
        data = self.make_data()
        data[1]['score_notes'] = ''

        has_errors, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertFalse(has_errors)
        self.assertFalse(cleaned[0]['errors'])
        self.assertFalse(cleaned[1]['errors'])
        self.assertFalse(cleaned[2]['errors'])
        self.assertFalse(cleaned[3]['errors'])

    def test_request_ID_wrong_format(self):
        data = self.make_data()
        data[0]['request_id'] = '1.23.4'
        data[1]['request_id'] = ' '
        data[2]['request_id'] = '-123'
        data[3]['request_id'] = '.0'

        has_errors, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertTrue(has_errors)
        for i in range(4):
            self.assertTrue(cleaned[i]['errors'])
            self.assertIn('Request ID is not an integer value.',
                          cleaned[i]['errors'], i)

    def test_score_manual_wrong_format(self):
        data = self.make_data()
        data[0]['score_manual'] = '1.23.4'
        data[1]['score_manual'] = ' '
        data[2]['score_manual'] = '.0'
        data[3]['score_manual'] = '-123'

        has_errors, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertTrue(has_errors)
        for i in range(3):
            self.assertTrue(cleaned[i]['errors'])
            self.assertIn('Manual score is not an integer value.',
                          cleaned[i]['errors'], i)

        # last entry should be valid
        self.assertFalse(cleaned[3]['errors'])

    def test_request_ID_not_matching(self):
        data = self.make_data()
        data[0]['request_id'] = '3333'

        has_errors, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertTrue(has_errors)
        self.assertTrue(cleaned[0]['errors'])
        self.assertIn('Request ID doesn\'t match any request.',
                      cleaned[0]['errors'])
        self.assertFalse(cleaned[1]['errors'])
        self.assertFalse(cleaned[2]['errors'])
        self.assertFalse(cleaned[3]['errors'])


class UpdateTrainingRequestManualScore(CSVBulkUploadTestBase):
    """
    Testing scenarios:
    * requests get updated correctly
    """

    def test_requests_updated(self):
        # prepare data
        data = self.make_data()

        # check and clean data
        errors_occur, cleaned = clean_upload_trainingrequest_manual_score(data)
        self.assertFalse(errors_occur)

        # make sure so far nothing changed
        self.tr1.refresh_from_db()
        self.tr2.refresh_from_db()
        self.tr3.refresh_from_db()
        self.tr4.refresh_from_db()
        self.assertEqual(self.tr1.score_manual, 10)
        self.assertEqual(self.tr2.score_manual, -10)
        self.assertEqual(self.tr3.score_manual, 0)
        self.assertEqual(self.tr4.score_manual, None)

        records_updated = update_manual_score(cleaned)
        # 4 records should be updated: self.tr1, self.tr2, self.tr3, self.tr4
        self.assertEqual(records_updated, 4)
        # make sure requests updated
        self.tr1.refresh_from_db()
        self.tr2.refresh_from_db()
        self.tr3.refresh_from_db()
        self.tr4.refresh_from_db()
        self.assertEqual(self.tr1.score_manual, -10)
        self.assertEqual(self.tr2.score_manual, 0)
        self.assertEqual(self.tr3.score_manual, 10)
        self.assertEqual(self.tr4.score_manual, 0)
