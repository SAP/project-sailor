"""Other utility functions that don't fit into any of the specific modules."""

from collections.abc import Iterable
import logging
import warnings


# this warning concerns the interactive use case
class DataNotFoundWarning(Warning):
    """Use this warning to indicate that a query-like function returned an empty result."""

    def __init__(self, message=None):
        message = "No data found for given parameters." if message is None else message
        super().__init__(message)


def _is_non_string_iterable(obj):
    if issubclass(obj.__class__, str):
        return False
    return isinstance(obj, Iterable)


def warn_and_log(message, logger_name, stacklevel=1, category=None):
    """Convert warnings into logs to simplify logging setup for users."""
    logger = logging.getLogger(logger_name)
    logger.warning(message)
    warnings.warn(message, category=category, stacklevel=stacklevel)
