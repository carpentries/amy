from django.dispatch import Signal as DjangoSignal


class Signal(DjangoSignal):
    signal_name: str  # TODO: consider using enum

    def __init__(self, *args, **kwargs):
        self.signal_name = kwargs.pop("signal_name")
        super().__init__(*args, **kwargs)


# Scheduled to run immediately after action (so roughly up to 1 hour later).
instructor_badge_awarded_signal = Signal(signal_name="instructor_badge_awarded")
instructor_confirmed_for_workshop_signal = Signal(
    signal_name="instructor_confirmed_for_workshop"
)
instructor_declined_from_workshop_signal = Signal(
    signal_name="instructor_declined_from_workshop"
)
instructor_signs_up_for_workshop_signal = Signal(
    signal_name="instructor_signs_up_for_workshop"
)
persons_merged_signal = Signal(signal_name="persons_merged")
