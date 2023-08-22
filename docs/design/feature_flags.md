# Feature flags in AMY

## What are feature flags?

Feature flags are a way to enable or disable features in a software
application. They are used to enable gradual rollouts of new features, A/B
testing, and to enable or disable features for specific users.

## How are feature flags implemented in AMY?

AMY uses the [django-flags](https://cfpb.github.io/django-flags/) package to implement feature flags.

## How do I add a new feature flag?

Extend `FLAGS` setting in `config/settings.py` with a new flag. For example:

```python
FLAGS = {
    "EMAIL_MODULE": [
        {"condition": "anonymous", "value": False, "required": True},
        {"condition": "parameter", "value": "enable_email_module=true"},
        {"condition": "session", "value": "enable_email_module"},
    ],
}
```

You can read about the different conditions in the [django-flags documentation](https://cfpb.github.io/django-flags/conditions/).

## How do I use a feature flag in my code?

1. To enable a function based on a feature flag, use the `feature_flag_enabled` decorator from `workshops.utils.feature_flags` module.
2. To enable a template block based on a feature flag, use the `flag_enabled` template tag from `django-flags` module (`{% load feature_flags %}`).

`EMAIL_MODULE` is a good feature flag example that can be tracked in the code to see how it works.

## How to use feature flags view to enable or disable a flag?

This view operates on specific conditions set in `FLAGS` setting in `config/settings.py`.

First, a `parameter` condition must be set with a value `xyz=true`. This will enable the flag for the user if the user visits a URL with `?xyz=true` parameter. For example, `https://amy.carpentries.org/?xyz=true`.
However, by default the URL is not persistent, so if the user changes the page to a one without this parameter, the flag will be disabled again.
To circumvent this, a special middleware was created that will save the flag parameter in the session if user's request path passes the `parameter` condition.

When combined with a `session` condition, such feature flag will stay enabled until the user logs out or uses the "Disable" link.

Disable link is also handled through the special middleware and it only accepts `?xyz=false` format.
