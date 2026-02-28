from django.test import TestCase

import src.emails.signals
from src.emails.signals import ALL_SIGNALS, Signal, SignalNameEnum


class TestSignalName(TestCase):
    def test_choices(self) -> None:
        """Check if SignalName.choices() returns all defined signals."""
        # Arrange
        signal_names = {item.signal_name for item in ALL_SIGNALS}

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
        """All SignalNameEnum values should have corresponding Signal instances."""
        # Arrange
        signal_name_values = {signal_name.value for signal_name in SignalNameEnum}

        # Act & Assert
        for name in signal_name_values:
            signal_instance_name = f"{name}_signal"
            self.assertIn(signal_instance_name, src.emails.signals.__dict__)
            self.assertIsInstance(src.emails.signals.__dict__[signal_instance_name], Signal)

    def test_receiver_connected(self) -> None:
        # Arrange
        signals = {
            (signal_variable_name, src.emails.signals.__dict__[signal_variable_name])
            for signal_variable_name in src.emails.signals.__dict__
            if signal_variable_name.endswith("_signal")
        }
        # Act & Assert
        for variable_name, signal in signals:
            self.assertEqual(len(signal.receivers), 1, variable_name)
