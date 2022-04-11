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


class WarningAdapter(logging.LoggerAdapter):
    """Allow a logger to convert warnings logs into real warnings to simplify logging setup for users."""

    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})

    def log_with_warning(self, msg, warning_stacklevel=1, warning_category=None):
        """Delegate a warning call to the underlying logger and trigger a real warning with the same message."""
        warnings.warn(msg, category=warning_category, stacklevel=warning_stacklevel + 1)
        self.log(logging.WARNING, msg)

    def log(self, level, msg, *args, **kwargs):
        """Delegate a log call to LoggerAdapter.log, after adjusting the stacklevel for introduced stack layers."""
        stacklevel_offset = 3
        kwargs['stacklevel'] = kwargs.get('stacklevel', 1) + stacklevel_offset
        super().log(level, msg, *args, **kwargs)
