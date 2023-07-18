from typing import TypedDict

from django.http import HttpRequest


class InstructorConfirmedKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    instructor_recruitment_id: int
    instructor_recruitment_signup_id: int


class InstructorDeclinedKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    instructor_recruitment_id: int
    instructor_recruitment_signup_id: int


class InstructorSignupKwargs(TypedDict):
    request: HttpRequest
    person_id: int
    event_id: int
    instructor_recruitment_id: int
    instructor_recruitment_signup_id: int


class PersonsMergedKwargs(TypedDict):
    request: HttpRequest
    person_a_id: int
    person_b_id: int
    selected_person_id: int
