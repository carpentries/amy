from django.contrib.postgres.forms import SplitArrayField


class FlexibleSplitArrayField(SplitArrayField):
    """Allow to dynamically change size of SplitArrayField and Widget."""

    def change_size(self, new_size: int) -> None:
        self.size = new_size
        self.widget.size = new_size
