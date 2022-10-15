import csv
from io import TextIOBase

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction


def upload_trainingrequest_manual_score_csv(stream: TextIOBase):
    """Read manual score entries from CSV and return a JSON-serializable
    list of dicts.

    The input `stream` should be a file-like object that returns
    Unicode data.

    "Serializability" is required because we put this data into session.  See
    https://docs.djangoproject.com/en/1.7/topics/http/sessions/ for details.
    """
    from workshops.models import TrainingRequest

    result = []
    reader = csv.DictReader(stream)

    for row in reader:
        # skip empty lines in the CSV
        if not any(row.values()):
            continue

        entry = {}
        for col in TrainingRequest.MANUAL_SCORE_UPLOAD_FIELDS:
            try:
                entry[col] = row[col].strip()
            except (KeyError, IndexError, AttributeError):
                # either `col` is not in `entry`, or not in `row`, or
                # `.strip()` doesn't work (e.g. `row[col]` gives `None` instead
                # of string)
                entry[col] = None

        entry["errors"] = None

        result.append(entry)

    return result


def clean_upload_trainingrequest_manual_score(data):
    """
    Verify that uploaded data is correct.  Show errors by populating `errors`
    dictionary item.  This function changes `data` in place.
    """
    from workshops.models import TrainingRequest

    clean_data = []
    errors_occur = False

    for item in data:
        errors = []

        obj = None
        request_id = item.get("request_id", None)
        if not request_id:
            errors.append("Request ID is missing.")
        else:
            try:
                num_request_id = int(request_id)
                if num_request_id < 0:
                    raise ValueError("Request ID should not be negative")
            except (ValueError, TypeError):
                errors.append("Request ID is not an integer value.")
            else:
                try:
                    obj = TrainingRequest.objects.get(pk=num_request_id)
                except TrainingRequest.DoesNotExist:
                    errors.append("Request ID doesn't match any request.")
                except TrainingRequest.MultipleObjectsReturned:
                    errors.append("Request ID matches multiple requests.")

        score = item.get("score_manual", None)
        score_manual = None
        if not score:
            errors.append("Manual score is missing.")
        else:
            try:
                score_manual = int(score)
            except (ValueError, TypeError):
                errors.append("Manual score is not an integer value.")

        score_notes = str(item.get("score_notes", ""))

        if errors:
            errors_occur = True

        clean_data.append(
            dict(
                object=obj,
                score_manual=score_manual,
                score_notes=score_notes,
                errors=errors,
            )
        )
    return errors_occur, clean_data


def update_manual_score(cleaned_data):
    """Updates manual score for selected objects.

    `cleaned_data` is a list of dicts, each dict has 3 fields:
    * `object` being the selected Training Request
    * `score_manual` - manual score to be applied
    * `score_notes` - notes regarding that manual score.
    """
    from workshops.models import TrainingRequest

    records = 0
    with transaction.atomic():
        for item in cleaned_data:
            try:
                obj = item["object"]
                score_manual = item["score_manual"]
                score_notes = item["score_notes"]
                records += TrainingRequest.objects.filter(pk=obj.pk).update(
                    score_manual=score_manual,
                    score_notes=score_notes,
                )
            except (IntegrityError, ValueError, TypeError, ObjectDoesNotExist) as e:
                raise e
    return records
