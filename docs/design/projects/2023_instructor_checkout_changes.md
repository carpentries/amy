# Instructor Checkout Changes

[GitHub project](https://github.com/carpentries/amy/projects/12).

In mid-2023, the checkout requirements for Instructor Training were updated.

## Previous design

Three steps:
* Lesson Contribution (submitted by trainee through AMY)
* Community Discussion (attendees submitted by host through a Google Form)
* Demo (attendees & pass/fail assessment submitted by host through a Google Form)

These steps were defined as `TrainingRequirement`s and progress by trainees was stored as `TrainingProgress` objects.

## New design

Three updated steps:
* Get Involved - any contribution, such as a GitHub contribution, supporting a workshop, or attending a Community Discussion (submitted by trainee through AMY)
* Welcome Session (attendees submitted by host through a Google Form)
* Demo (attendees & pass/fail assessment submitted by host through a Google Form)

The "Community Discussion" `TrainingRequirement` was renamed to "Welcome Session," but otherwise left unchanged. 

The "Lesson Contribution" `TrainingRequirement` was changed more significantly. First, it was renamed to "Get Involved." Second, a new model `Involvement` was developed to store the different activities that a trainee might complete as part of this step. The `TrainingProgress` model was then updated to store an `Involvement` if needed, plus a possible date, URL (already supported), and notes from the trainee. Finally, the instructor dashboard was updated to allow the trainee to submit their activity.

Also as part of this project:
* 'Discarded' status field was removed from `TrainingProgress`
* Deprecated lesson-program-specific `TrainingRequirement`s were removed (e.g. "SWC Demo" or "LC Homework")