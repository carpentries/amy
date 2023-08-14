from typing import TypedDict

from django.http import HttpRequest

from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Award, Event, Person


class InstructorBadgeAwardedKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    award_id: int


class InstructorBadgeAwardedContext(TypedDict):
    person: Person
    award: Award


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
