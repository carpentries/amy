# New group application workflow

When a partner asks us for a training for a group of people: 

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

## Registration for training

When a trainee submits training request in response to the email sent in step 4:

1. Admin goes to "training requests" page.

1. Admin goes to details of the requests that was submitted. 

1. Admin manually accepts the request and matches it with the right Person record, which is proposed by AMY since we already have that person in database.

## Confirmation of interest in the training

When a trainee replies to email sent in step 5. and confirms interest in the training: 

1. Admin do nothing.

## Resignation from the training

When a trainee replies to email sent in step 5. and resigns from the training: 

1. Admin unassignes her from the training
 
1. If the trainee is not interested in training at all any more, Admin discards her training request.

# New features

This workflow requires the following new features in "trainees" view:

- Filter trainees by presence of training request.

- Bulk email selected trainees with three presets of email content.

- Column with list of training requests.