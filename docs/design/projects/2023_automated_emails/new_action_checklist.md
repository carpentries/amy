# Implementing a new action

## Checklist

1. Add new action signal name to `emails.signals.SignalNameEnum` enum.
2. Define the context TypedDict in `emails.types` module. This should be a dictionary
   with keys and types of values that will be passed to the email template as context.
3. Define the kwargs TypedDict in `emails.types` module. This should be a dictionary
   with keys and types of values that will be passed to the action's constructor (when
   the signal for email is being sent).
4. Define the action class in a new module in `emails.actions` package. This class should
   inherit from `BaseAction` class and implement all required methods.
5. If the action should allow for updating or cancelling, define additional classes
   inheriting from `BaseActionUpdate` and `BaseActionCancel` respectively.
6. Create receivers as instances of the action classes. Link the receivers to the
   appropriate signals in `emails.signals` module:
   ```python
   receiver = MyAction()
   signal.connect(receiver)
   ```

7. If the action consists of scheduling, updating, and cancelling, create `action_strategy` and `run_action_strategy` functions. Follow examples from other actions.


## Using a new action

If the action contains a strategy, then using it is quite simple:

```python
run_action_strategy(
    action_strategy(object),
    request,
    object,
)
```

Strategies may accept other parameters, but the selected strategy and request (as in
Django view request) are required.

The code above needs to be used in the places where we know user has taken some action (e.g. edited an
event) and we want to either trigger a new scheduled email, update existing scheduled email, or cancel
such email.
