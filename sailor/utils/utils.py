"""Other utility functions that don't fit into any of the specific modules."""


# this warning concerns the interactive use case
class DataNotFoundWarning(Warning):
    """Use this warning to indicate that a query-like function returned an empty result."""

    def __init__(self, message=None):
        message = "No data found for given parameters." if message is None else message
        super().__init__(message)
