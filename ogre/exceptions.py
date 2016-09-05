"""OGRe Error Handler"""


class OGReError(Exception):

    """Create exceptions that contain an origin reference and a message."""

    def __init__(self, message, source=None):
        super(OGReError, self).__init__()
        self.message = message
        self.source = source

    def __str__(self):
        return '{0}{1}'.format('' if self.source is None else self.source + ': ', self.message)


class OGReLimitError(OGReError):

    pass


class OGReQueryError(OGReError):

    pass
