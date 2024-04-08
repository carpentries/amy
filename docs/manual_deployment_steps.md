# Release-Specific Manual Deployment Steps

This document tracks steps that must be completed manually before or after the specified release is deployed.

## v4.3

1. Deploy the worker correctly to PROD environment
2. Prepare production email worker account only with `knox.add_authtoken` permission and active status
    * put this account credentials in SSM parameters `/{stage}/email-worker/token_username` and `/{stage}/email-worker/token_password`

### After

* Update Redash queries about training requests to change `group_name` to `member_code` (in line with changes to the `TrainingRequest` model).

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
