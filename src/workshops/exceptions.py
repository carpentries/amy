class InternalError(Exception):
    pass


class WrongWorkshopURL(Exception):
    """Raised when we fall back to reading metadata from event's YAML front
    matter, which requires a link to GitHub raw hosted file, but we can't get
    that link because provided URL doesn't match Event.WEBSITE_REGEX or Event.REPO_REGEX
    (see `generate_url_to_event_index` in workshops.utils.metadata)."""

    def __init__(self, msg: str):
        # Store the error message in class field so that it can be retrieved later.
        # This circumvents CodeQL error when the exception instance `e` was stringified
        # `str(e)` - now the code addresses `e.msg` directly.
        self.msg = msg
        super().__init__()
