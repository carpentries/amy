from django.dispatch import Signal

# signal generated when a comment regarding specific object should be saved
# arguments: "content_object", "comment", "timestamp"
create_comment_signal = Signal()

# signal generated when a Person object has been archived
# arguments: "person"
person_archived_signal = Signal()
