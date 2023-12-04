# Member code enforcement

[GitHub project](https://github.com/carpentries/amy/projects/15).

In early 2024, the membership team planned to start enforcing that all preapproved IT applications and workshop requests should include a valid and active member code (a.k.a. registration code, group code)

In mid-2023, the checkout requirements for Instructor Training were updated. As the relevant changes were made to AMY to support this update, the project also expanded to include improvements to the training progress view for trainees.

## Feature flag

The `ENFORCE_MEMBER_CODES` [feature flag](../feature_flags.md) controls whether validity checks are performed on member codes. If set to `True` in the Django admin panel, validity checks will be performed on all submissions. If set to `False`, no checks will be performed (i.e. all codes will be accepted). The value of the flag does **not** affect whether the `member_code` field is displayed on forms or in views.

## Instructor Training Application Form

### Previous design

The form had a field for the member code, but it was optional and not checked for validity.

### New design

The member code field is now required for preapproved trainees, and will raise an error if the entered code is invalid, inactive, or has no seats remaining. However, to avoid forcing the trainee to speak to their membership contact (who may in turn need to speak to us) and wait for the resolution, there is a checkbox to override the invalid code and submit the form anyway.

On the admin side, when viewing all training requests, there is now a filter to show applications where the override was used, so these applications can easily be manually checked.

## Workshop Request Form

### Previous design

The workshop request form did not include a field for the member code. Instead, the WAT would match workshops up with memberships manually.

### New design

The form now includes a field for the member code. This field will raise an error if the entered code is invalid or inactive. Unlike the instructor training application, there is no option to override an invalid code.

On the admin side, when viewing a workshop request, there is an info box showing the associated membership for the member code (if applicable) and how many workshops that membership has remaining. There is also a filter on the workshop requests page to find requests that came from a member organisation but didn't use any member code - this may happen if multiple groups at the same institution find The Carpentries independently of each other.

## Other changes

Other features added as part of this project:

* When creating an Event from a workshop request, autofill the membership based on the member code
* When adding a learner Task for a trainee at a TTT event, autofill the membership based on the member code in the trainee's application
* When bulk matching trainees to training, use the new "Automatically match seats to memberships" option to assign each trainee to a membership seat based on the member code in their application (as an alternative to assigning all matched trainees to the same membership)
* Update email autoresponses to include member code information
* Include a question about the Eventbrite event that a preapproved trainee has signed up for (if applicable) and allow admins to filter applications by Eventbrite event URLs or IDs.
* Updates to other questions on the instructor training application
