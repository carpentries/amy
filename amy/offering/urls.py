from django.urls import include, path

from offering import views

urlpatterns = [
    path(
        "accounts/",
        include(
            [
                path(
                    "",
                    views.AccountList.as_view(),  # type: ignore
                    name="account-list",
                ),
                path(
                    "create/",
                    views.AccountCreate.as_view(),  # type: ignore
                    name="account-create",
                ),
            ]
        ),
    ),
    path(
        "accounts/<uuid:pk>/",
        include(
            [
                path(
                    "",
                    views.AccountDetails.as_view(),  # type: ignore
                    name="account-details",
                ),
                path(
                    "edit/",
                    views.AccountUpdate.as_view(),  # type: ignore
                    name="account-update",
                ),
                path(
                    "delete/",
                    views.AccountDelete.as_view(),  # type: ignore
                    name="account-delete",
                ),
                path(
                    "owners/",
                    views.AccountOwnersUpdate.as_view(),  # type: ignore
                    name="account-owners-update",
                ),
            ]
        ),
    ),
    path(
        "benefits/",
        include(
            [
                path(
                    "",
                    views.BenefitList.as_view(),  # type: ignore
                    name="benefit-list",
                ),
                path(
                    "create/",
                    views.BenefitCreate.as_view(),  # type: ignore
                    name="benefit-create",
                ),
            ]
        ),
    ),
    path(
        "benefits/<uuid:pk>/",
        include(
            [
                path(
                    "",
                    views.BenefitDetails.as_view(),  # type: ignore
                    name="benefit-details",
                ),
                path(
                    "edit/",
                    views.BenefitUpdate.as_view(),  # type: ignore
                    name="benefit-update",
                ),
                path(
                    "delete/",
                    views.BenefitDelete.as_view(),  # type: ignore
                    name="benefit-delete",
                ),
            ]
        ),
    ),
    path(
        "account-benefits/",
        include(
            [
                path(
                    "",
                    views.AccountBenefitList.as_view(),  # type: ignore
                    name="account-benefit-list",
                ),
                path(
                    "create/",
                    views.AccountBenefitCreate.as_view(),  # type: ignore
                    name="account-benefit-create",
                ),
            ]
        ),
    ),
    path(
        "account-benefits/<uuid:pk>/",
        include(
            [
                path(
                    "",
                    views.AccountBenefitDetails.as_view(),  # type: ignore
                    name="account-benefit-details",
                ),
                path(
                    "edit/",
                    views.AccountBenefitUpdate.as_view(),  # type: ignore
                    name="account-benefit-update",
                ),
                path(
                    "delete/",
                    views.AccountBenefitDelete.as_view(),  # type: ignore
                    name="account-benefit-delete",
                ),
            ]
        ),
    ),
    path(
        "event-categories/",
        include(
            [
                path(
                    "",
                    views.EventCategoryList.as_view(),  # type: ignore
                    name="event-category-list",
                ),
                path(
                    "create/",
                    views.EventCategoryCreate.as_view(),  # type: ignore
                    name="event-category-create",
                ),
            ]
        ),
    ),
    path(
        "event-categories/<uuid:pk>/",
        include(
            [
                path(
                    "",
                    views.EventCategoryDetails.as_view(),  # type: ignore
                    name="event-category-details",
                ),
                path(
                    "edit/",
                    views.EventCategoryUpdate.as_view(),  # type: ignore
                    name="event-category-update",
                ),
                path(
                    "delete/",
                    views.EventCategoryDelete.as_view(),  # type: ignore
                    name="event-category-delete",
                ),
            ]
        ),
    ),
]
