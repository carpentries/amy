from django.urls import include, path

from . import views

urlpatterns = [
    path(
        "processes/",
        views.InstructorRecruitmentList.as_view(),
        name="all_instructorrecruitment",
    ),
    path(
        "process/add/<int:event_id>/",
        views.InstructorRecruitmentCreate.as_view(),
        name="instructorrecruitment_add",
    ),
    path(
        "process/<int:pk>/",
        include(
            [
                path(
                    "",
                    views.InstructorRecruitmentDetails.as_view(),
                    name="instructorrecruitment_details",
                ),
                path(
                    "add-signup",
                    views.InstructorRecruitmentAddSignup.as_view(),
                    name="instructorrecruitment_add_signup",
                ),
                path(
                    "change-state",
                    views.InstructorRecruitmentChangeState.as_view(),
                    name="instructorrecruitment_changestate",
                ),
            ]
        ),
    ),
    path(
        "signup/<int:pk>/",
        include(
            [
                path(
                    "change-state",
                    views.InstructorRecruitmentSignupChangeState.as_view(),
                    name="instructorrecruitmentsignup_changestate",
                ),
                path(
                    "edit",
                    views.InstructorRecruitmentSignupUpdate.as_view(),
                    name="instructorrecruitmentsignup_edit",
                ),
            ]
        ),
    ),
]
