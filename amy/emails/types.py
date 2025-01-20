from datetime import date
from enum import StrEnum
from typing import TypedDict

from django.http import HttpRequest

from extrequests.models import SelfOrganisedSubmission
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import (
    Award,
    Event,
    Membership,
    Organization,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)


class InstructorBadgeAwardedKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    award_id: int


class InstructorBadgeAwardedContext(TypedDict):
    person: Person
    award: Award | None
    award_id: int


class InstructorConfirmedKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    instructor_recruitment_id: int
    instructor_recruitment_signup_id: int


class InstructorConfirmedContext(TypedDict):
    person: Person
    event: Event
    instructor_recruitment_signup: InstructorRecruitmentSignup


class InstructorDeclinedKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    instructor_recruitment_id: int
    instructor_recruitment_signup_id: int


class InstructorDeclinedContext(TypedDict):
    person: Person
    event: Event
    instructor_recruitment_signup: InstructorRecruitmentSignup


class InstructorSignupKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    instructor_recruitment_id: int
    instructor_recruitment_signup_id: int


class InstructorSignupContext(TypedDict):
    person: Person
    event: Event
    instructor_recruitment_signup: InstructorRecruitmentSignup


class AdminSignsInstructorUpKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    instructor_recruitment_id: int
    instructor_recruitment_signup_id: int


class AdminSignsInstructorUpContext(TypedDict):
    person: Person
    event: Event
    instructor_recruitment_signup: InstructorRecruitmentSignup


class PersonsMergedKwargs(TypedDict):
    request: HttpRequest
    person_a_id: int
    person_b_id: int
    selected_person_id: int


class PersonsMergedContext(TypedDict):
    person: Person


class InstructorTaskCreatedForWorkshopKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    task_id: int


class InstructorTaskCreatedForWorkshopContext(TypedDict):
    person: Person
    event: Event
    task: Task | None
    task_id: int | None


class InstructorTrainingApproachingKwargs(TypedDict):
    request: HttpRequest
    event: Event
    event_start_date: date


class InstructorTrainingApproachingContext(TypedDict):
    event: Event
    instructors: list[Person]


class InstructorTrainingCompletedNotBadgedKwargs(TypedDict):
    request: HttpRequest
    person: Person
    training_completed_date: date


class InstructorTrainingCompletedNotBadgedContext(TypedDict):
    person: Person
    passed_requirements: list[TrainingProgress]
    not_passed_requirements: list[TrainingProgress]
    not_graded_requirements: list[TrainingRequirement]
    training_completed_date: date


class NewMembershipOnboardingKwargs(TypedDict):
    request: HttpRequest
    membership: Membership


class NewMembershipOnboardingContext(TypedDict):
    membership: Membership


class HostInstructorsIntroductionContext(TypedDict):
    assignee: Person | None
    event: Event
    workshop_host: Organization | None
    host: Person | None
    instructors: list[Person]


class HostInstructorsIntroductionKwargs(TypedDict):
    event: Event


class RecruitHelpersContext(TypedDict):
    event: Event
    assignee: Person | None
    instructors: list[Person]
    hosts: list[Person]


class RecruitHelpersKwargs(TypedDict):
    event: Event
    event_start_date: date


class PostWorkshop7DaysContext(TypedDict):
    event: Event
    hosts: list[Person]
    instructors: list[Person]
    helpers: list[Person]
    assignee: Person | None


class PostWorkshop7DaysKwargs(TypedDict):
    event: Event
    event_end_date: date


class NewSelfOrganisedWorkshopContext(TypedDict):
    event: Event
    self_organised_submission: SelfOrganisedSubmission
    assignee: Person | None
    workshop_host: Organization
    short_notice: bool


class NewSelfOrganisedWorkshopKwargs(TypedDict):
    event: Event
    self_organised_submission: SelfOrganisedSubmission


class AskForWebsiteContext(TypedDict):
    event: Event
    instructors: list[Person]
    assignee: Person | None


class AskForWebsiteKwargs(TypedDict):
    event: Event
    event_start_date: date


class StrategyEnum(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    CANCEL = "cancel"
    NOOP = "noop"
