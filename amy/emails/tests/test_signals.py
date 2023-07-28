from django.test import TestCase

import emails.signals
from emails.signals import Signal, SignalNameEnum


class TestSignalName(TestCase):
    def test_choices(self) -> None:
        """Check if SignalName.choices() returns all defined signals."""
        # Arrange
        signal_names = {
            emails.signals.__dict__[signal].signal_name
            for signal in emails.signals.__dict__
            if signal.endswith("_signal")
        }

        # Act
        choices = SignalNameEnum.choices()

        # Assert
        for choice in choices:
            self.assertIn(choice[0], choice[1])

        self.assertEqual({choice[0] for choice in choices}, signal_names)


class TestSignal(TestCase):
    def test_signal_name(self) -> None:
        """Check if Signal contains an attribute `signal_name`."""
        # Arrange
        signal = Signal(signal_name="test_signal_name", context_type=dict)

        # Act
        signal_name = signal.signal_name

        # Assert
        self.assertEqual(signal_name, "test_signal_name")


class TestCreatedSignals(TestCase):
    def test_signal_name_values(self) -> None:
        """All signals should be reflected in SignalName values, and all SignalName
        values should be reflected by Signal instances."""
        # Arrange
        signal_name_values = {signal_name.value for signal_name in SignalNameEnum}
        signals = {
            signal[:-7]  # remove "_signal" suffix from actual name
            for signal in emails.signals.__dict__
            if signal.endswith("_signal")
        }

        # Assert
        self.assertEqual(signals, signal_name_values)

    def test_signal_names_correct(self) -> None:
        """Every signal should use a corresponding name."""
        # Arrange
        signals = {
            (
                signal[:-7],  # remove "_signal" suffix from actual name
                emails.signals.__dict__[signal].signal_name,  # attribute signal name
            )
            for signal in emails.signals.__dict__
            if signal.endswith("_signal")
        }

        # Assert
        for signal_name, signal_name_attribute in signals:
            self.assertEqual(signal_name, signal_name_attribute)

    def test_receiver_connected(self) -> None:
        # Arrange
        signals = {
            emails.signals.__dict__[signal]
            for signal in emails.signals.__dict__
            if signal.endswith("_signal")
        }
        # Act & Assert
        for signal in signals:
            self.assertEqual(len(signal.receivers), 1, signal.signal_name)
