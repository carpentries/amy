"""
How to use RQ Scheduler in order to schedule these jobs:
>>> from datetime import timedelta
>>> import django_rq
>>> scheduler = django_rq.get_scheduler('default')
>>> job = scheduler.enqueue_in(timedelta(minutes=1), blocking, 30)
"""

import random
import time

from django.core import mail


def blocking(t=60):
    print(f"Setting up 'blocking' (t={t})")
    time.sleep(t)
    print("After sleep ('blocking').")


def fake_results(t=60):
    print(f"'fake_results' (t={t}) started")
    r = random.random()
    time.sleep(t)
    print(f"'fake_results' (t={t}) finished (results={r})")
    return r


def send_test_email():
    print(f"'send_test_email' started")
    mail.send_mail('Subject here',
                   'Long message',
                   'from@example.com',
                   ['to@example.org'],
                   fail_silently=False)
    print(f"'send_test_email' finished")
    print("Testing the email outbox")
    print(mail.outbox)
    print('-' * 50)
