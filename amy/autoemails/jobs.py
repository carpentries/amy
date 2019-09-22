import random
import time


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
