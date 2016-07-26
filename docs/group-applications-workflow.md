1. Admin creates an event with slug. Admin remembers the slug.

1. Admin bulk uploads people sent by the partner and assigns them to the training. This requires to use CSV file with five columns:

    - personal name,
    - family name,
    - email address,
    - the training slug (all rows with the same value) and
    - role ('learner' in all rows).

1. Admin goes to "trainees" page and filter by training. That way, Admin can list exactly the same set of people that he uploaded. In the same view, Admin can filter by whether an training request was sent or not.

1. Admin filters only trainees who haven't sent training request yet (and are assigned to the training) and bulk email them. This email contains link to training request form, with group name. Training id is not included in the link, because trainees are already matched with the training.

1. Admin filters only trainees who already have sent training request (and are assigned to the training) and bulk email them. In this email, we ask them to confirm if they're still interested in the training.

1. One of trainees submits training request form.

1. Admin goes to "training requests" page and, then, to details of the requests that was submitted. Admin manually accepts the request and matches it with the right Person record, which is proposed by AMY since we already have that person in database.

1. One of trainees replies to email and confirms that she's still interested in the training.

1. Issue: How do we indicate that fact in AMY? What should Admin do?

1. One of trainees replies to email and resigns from the training.

1. Admin unassignes her from the training and discard her training request.

This workflow requires the following new features in "trainees" view:

- Filter trainees by presence of training request.

- Bulk email selected trainees with two presets of email content.

- Column with list of training requests.

And "filter by training" in "training requests" page.