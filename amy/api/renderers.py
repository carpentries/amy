from rest_framework_csv.renderers import CSVRenderer

from api.serializers import (
    TrainingRequestForManualScoringSerializer,
    TrainingRequestWithPersonSerializer,
)


class TrainingRequestCSVColumns:
    translation_labels = {
        "created_at": "Created at",
        "last_updated_at": "Last updated at",
        "state": "State",
        "person": "Matched Trainee",
        "person_id": "Matched Trainee ID",
        "awards": "Badges",
        "training_tasks": "Training Tasks",
        "review_process": "Application Type",
        "group_name": "Registration Code",
        "personal": "Personal",
        "middle": "Middle",
        "family": "Family",
        "email": "Email",
        "secondary_email": "Secondary email",
        "github": "GitHub username",
        "underrepresented": "Underrepresented",
        "underrepresented_details": "Underrepresented (reason)",
        "occupation": "Occupation",
        "occupation_other": "Occupation (other)",
        "affiliation": "Affiliation",
        "location": "Location",
        "country": "Country",
        "underresourced": "Underresourced institution",
        "domains": "Expertise areas",
        "domains_other": "Expertise areas (other)",
        "nonprofit_teaching_experience": "Non-profit teaching experience",
        "previous_involvement": "Previous Involvement",
        "previous_training": "Previous Training in Teaching",
        "previous_training_other": "Previous Training (other)",
        "previous_training_explanation": "Previous Training (explanation)",
        "previous_experience": "Previous Experience in Teaching",
        "previous_experience_other": "Previous Experience (other)",
        "previous_experience_explanation": "Previous Experience (explanation)",
        "programming_language_usage_frequency": "Programming Language Usage",
        "checkout_intent": "Intent to complete checkout",
        "teaching_intent": "Intent to teach workshops",
        "teaching_frequency_expectation": "Teaching Frequency Expectation",
        "teaching_frequency_expectation_other": "Teaching Frequency Expectation (other)",  # noqa: line too long
        "max_travelling_frequency": "Max Travelling Frequency",
        "max_travelling_frequency_other": "Max Travelling Frequency (other)",
        "reason": "Reason for undertaking training",
        "user_notes": "User notes",
        "training_completion_agreement": "Training completion agreement (yes/no)",
        "workshop_teaching_agreement": "Workshop teaching agreement (yes/no)",
        "data_privacy_agreement": "Data privacy agreement (yes/no)",
        "code_of_conduct_agreement": "Code of Conduct agreement (yes/no)",
    }

    def __init__(self):
        self.header = self.serializer.Meta.fields
        self.labels = {
            k: v for k, v in self.translation_labels.items() if k in self.header
        }


class TrainingRequestCSVRenderer(CSVRenderer, TrainingRequestCSVColumns):
    serializer = TrainingRequestWithPersonSerializer


class TrainingRequestManualScoreCSVRenderer(CSVRenderer, TrainingRequestCSVColumns):
    serializer = TrainingRequestForManualScoringSerializer
    format = "csv2"
