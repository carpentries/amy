from django.dispatch import Signal

# signal generated when a comment regarding specific object should be saved
create_comment_signal = Signal(
    providing_args=["content_object", "comment", "timestamp"]
)
# signal generated when a Person object has been archived
person_archived_signal = Signal(providing_args=["person"])
