# Release-Specific Manual Deployment Steps

This document tracks steps that must be completed manually before or after the specified release is deployed.

## v4.3

Nothing yet.

## v4.2

### Before

* Add variables to Ansible playbook to set `EMAIL_MODULE_ENABLED` flag

### After

* Run seeding scripts `seed_training_requirements.py` and `seed_involvements.py` on the server:
    ```
    $ source .venv/bin/postactivate
    $ .venv/bin/python manage.py runscript <script>
    ```
* Merge updated documentation to `develop`
