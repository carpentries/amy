# Release-Specific Manual Deployment Steps

This document tracks steps that must be completed manually before or after the specified release is deployed.

## v4.3

Nothing yet.

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
