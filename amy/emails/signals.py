from enum import StrEnum

from django.dispatch import Signal as DjangoSignal


class SignalName(StrEnum):
    instructor_badge_awarded = "instructor_badge_awarded"
    instructor_confirmed_for_workshop = "instructor_confirmed_for_workshop"
    instructor_declined_from_workshop = "instructor_declined_from_workshop"
    instructor_signs_up_for_workshop = "instructor_signs_up_for_workshop"
    persons_merged = "persons_merged"

    @staticmethod
    def choices() -> list[tuple[str, str]]:
        return [(signal_name.value, signal_name.value) for signal_name in SignalName]


class Signal(DjangoSignal):
    signal_name: SignalName

    def __init__(self, *args, **kwargs):
        self.signal_name = kwargs.pop("signal_name")
        super().__init__(*args, **kwargs)


# Scheduled to run immediately after action (so roughly up to 1 hour later).
instructor_badge_awarded_signal = Signal(
    signal_name=SignalName.instructor_badge_awarded
)
instructor_confirmed_for_workshop_signal = Signal(
    signal_name=SignalName.instructor_confirmed_for_workshop
)
instructor_declined_from_workshop_signal = Signal(
    signal_name=SignalName.instructor_declined_from_workshop
)
instructor_signs_up_for_workshop_signal = Signal(
    signal_name=SignalName.instructor_signs_up_for_workshop
)
persons_merged_signal = Signal(signal_name=SignalName.persons_merged)
