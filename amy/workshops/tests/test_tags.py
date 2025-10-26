from workshops.models import Tag
from workshops.tests.base import TestBase


class TestTagManager(TestBase):
    def setUp(self) -> None:
        super()._setUpTags()

    def test_main_tags(self) -> None:
        # Arrange
        expected = [
            Tag.objects.get(name="DC"),
            Tag.objects.get(name="ITT"),
            Tag.objects.get(name="LC"),
            Tag.objects.get(name="SWC"),
            Tag.objects.get(name="TTT"),
            Tag.objects.get(name="WiSE"),
        ]
        # Act
        tags = Tag.objects.main_tags().order_by("name")
        # Assert
        self.assertEqual(list(tags), expected)

    def test_carpentries_tags(self) -> None:
        # Arrange
        expected = [
            Tag.objects.get(name="DC"),
            Tag.objects.get(name="LC"),
            Tag.objects.get(name="SWC"),
        ]
        # Act
        tags = Tag.objects.carpentries().order_by("name")
        # Assert
        self.assertEqual(list(tags), expected)

    def test_strings(self) -> None:
        # Arrange
        expected = ["DC", "LC", "SWC"]
        # Act
        tags = Tag.objects.carpentries().order_by("name").strings()
        # Assert
        self.assertEqual(list(tags), expected)
