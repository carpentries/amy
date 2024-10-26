# Instructor Checkout Changes

[GitHub project](https://github.com/carpentries/amy/projects/12).

In mid-2023, the checkout requirements for Instructor Training were updated. As the relevant changes were made to AMY to support this update, the project also expanded to include improvements to the training progress view for trainees.

## Checkout steps

### Previous design

Three steps:
* Lesson Contribution (submitted by trainee through AMY)
* Community Discussion (attendees submitted by host through a Google Form)
* Demo (attendees & pass/fail assessment submitted by host through a Google Form)

These steps were defined as `TrainingRequirement`s and progress by trainees was stored as `TrainingProgress` objects.

### New design

Three updated steps:
* Get Involved - any contribution, such as a GitHub contribution, supporting a workshop, or attending a Community Discussion (submitted by trainee through AMY)
* Welcome Session (attendees submitted by host through a Google Form)
* Demo (attendees & pass/fail assessment submitted by host through a Google Form)

The "Community Discussion" `TrainingRequirement` was renamed to "Welcome Session," but otherwise left unchanged. 

The "Lesson Contribution" `TrainingRequirement` was changed more significantly. First, it was renamed to "Get Involved." Second, a new model `Involvement` was developed to store the different activities that a trainee might complete as part of this step. The `TrainingProgress` model was then updated to store an `Involvement` if needed, plus a possible date, URL (already supported), and notes from the trainee. Finally, the submission form on the instructor dashboard was updated to allow the trainee to submit their activity under the new system.

## Training Progress view

### Previous design

A trainee could see what steps they had passed. Any other step status was shown as 'not passed yet.'

The 90-day checkout deadline was not shown on the page; this deadline was only communicated by email.

The Lesson Contribution submission form was always available, and no detail of previous submissions was visible. This led to confusion: some trainees would make multiple submissions, or be unsure if their submission had gone through.

There was also no validation that the lesson contribution URL was associated with a GitHub repository owned by The Carpentries. The Instructor Training Team would often have to contact trainees to explain this error and ask them to resubmit.

### New design

The updated view was updated to show the state (passed/not evaluated yet/asked to repeat/failed) of each step. If training was passed, the page also displays the 90-day checkout deadline.

A summary of the trainee's Get Involved submission (if present) was added.

The Get Involved submission form (which replaced the Lesson Contribution submission form) was moved to a separate view. This allowed edit and delete functionality to be added to un-evaluated submissions. Checks were also added to prevent a trainee from making multiple submissions unless requested to do so.

Finally, validation was added to ensure submissions of GitHub contributions include a URL associated with a [Carpentries GitHub repository](https://docs.carpentries.org/topic_folders/communications/tools/github_organisations.html).

## Other changes

Also as part of this project:
* 'Discarded' status field was removed from `TrainingProgress`
* 'Evaluated by' field was removed from `TrainingProgress`
* Deprecated lesson-program-specific `TrainingRequirement`s were removed (e.g. "SWC Demo" or "LC Homework")
