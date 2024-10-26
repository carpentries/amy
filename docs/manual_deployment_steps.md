# Release-Specific Manual Deployment Steps

This document tracks steps that must be completed manually before or after the specified release is deployed.

## v4.3

### Before

#### Member docs

1. Check for TrainingProgress with non-unique combinations of `trainee` and `event` (excluding nulls), and remove duplicates.
This is required for the migration `workshops.0264_trainingprogress_unique_trainee_at_event` to succeed.

#### Automated emails

1. Deploy the worker correctly to PROD environment
2. Prepare production email worker account only with `knox.add_authtoken` permission and active status
    * put this account credentials in SSM parameters `/{stage}/email-worker/token_username` and `/{stage}/email-worker/token_password`

### After

* Update Redash queries about training requests to change `group_name` to `member_code` (in line with changes to the `TrainingRequest` model).
* Update new email templates in production before running the script to migrate emails from the old system - see https://github.com/carpentries/amy/issues/2707 for details.
* Run email migration script on the server: `./manage.py create_emails_for_existing_events`.

------------------------------------------------------------

## v4.2

### Before

* Add variables to Ansible playbook to set `EMAIL_MODULE_ENABLED` flag

### After

* Run seeding scripts `seed_training_requirements.py` and `seed_involvements.py` on the server:

    ```
    $ sudo su
    # cd /webapps/amy.carpentries.org/repo/
    # source .venv/bin/postactivate
    # .venv/bin/python3 manage.py runscript seed_involvements
    # .venv/bin/python3 manage.py runscript seed_training_requirements
    ```

* Merge updated documentation to `develop`
