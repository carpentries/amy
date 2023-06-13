from django.dispatch import Signal

# Scheduled to run immediately after action (so roughly up to 1 hour later).
instructor_signs_up_for_workshop_signal = Signal()
instructor_confirmed_for_workshop_signal = Signal()
instructor_declined_from_workshop_signal = Signal()
instructor_badge_awarded_signal = Signal()
persons_merged_signal = Signal()
