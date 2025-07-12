from django.urls import include, path

from offering import views

urlpatterns = [
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
