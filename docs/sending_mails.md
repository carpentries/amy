# Sending mails

## Command

It's possible to send annual "check your AMY data" mail to all instructors with
following command: `./manage.py instructor_activity`.

## Parameters

This command uses optional arguments:

`--send-out-for-real`
: You need to use this to *really* send the emails.

`--no-may-contact-only`
: By default, the command only send mails to people who agreed to receive them
(`may_contact == True`).  Setting this argument, the command will mail all of
our instructors.

`--django-mailing`
: This switch changes underlying sending mechanism. By default it uses `mail`
UNIX command.  See [Sending](#sending) for more information.

`-s SENDER`
`--sender SENDER`
: Set "From: " field value.  Default is `team@carpentries.org`.

## Sending

There are two mechanisms that `instructor_activity` can use.

### UNIX `mail` command

The way we use this command:

`mail -s "{subject}" -r {sender} {recipient} < {message}`

### Django mailing system

Django requires setting some envvars in order to send emails.

* `AMY_DEBUG=false`: required in order to send emails not to `/dev/null`
* `AMY_SECRET_KEY`: probably must have any string value
* `AMY_RECAPTCHA_PUBLIC_KEY`: must be present when not in debugging mode
* `AMY_RECAPTCHA_PRIVATE_KEY`: must be present when not in debugging mode
* `AMY_EMAIL_HOST`: SMTP server address
* `AMY_EMAIL_HOST_USER`: SMTP user
* `AMY_EMAIL_HOST_PASSWORD`: SMTP password
* `AMY_EMAIL_PORT=587`: default port for TLS SMTP
* `AMY_EMAIL_USE_TLS='true'`

Example usage:

```bash
AMY_SECRET_KEY='asdasdasd' AMY_DEBUG=false \
AMY_RECAPTCHA_PUBLIC_KEY='asdasdasd' AMY_RECAPTCHA_PRIVATE_KEY='asdasdasd' \
AMY_EMAIL_HOST='smtp.gmail.com' \
AMY_EMAIL_HOST_USER='amy-noreply@gmail.com' \
AMY_EMAIL_HOST_PASSWORD='a very hard password' \
AMY_EMAIL_PORT=587 AMY_EMAIL_USE_TLS='true' \
./manage.py instructor_activity --django-mailing --send-out-for-real
```
