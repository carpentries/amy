# Accessibility Testing in AMY

The automated tests aim to test one page corresponding to each template in `amy/templates` (including base templates and the `includes` subfolder).

The following pages cannot be effectively tested automatically at the moment. Problems include:

* page inaccessible to logged-in admin (`/terms/action_required)
* objects unavailable (e.g. no available signups for instructors to view)
* file upload required (bulk uploads)
* domain/slug required in URL, but organizations and events are randomly generated

```json
"http://127.0.0.1:8000/terms/action_required/",
"http://127.0.0.1:8000/dashboard/instructor/teaching_opportunities/<int:recruitment_pk>/signup",
"http://127.0.0.1:8000/requests/bulk_upload_training_request_scores/",
"http://127.0.0.1:8000/requests/bulk_upload_training_request_scores/confirm/",
"http://127.0.0.1:8000/fiscal/organization/<str:org_domain>/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/review_metadata_changes/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/delete/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/edit/",
"http://127.0.0.1:8000/workshops/persons/bulk_upload/confirm/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/validate/",
```