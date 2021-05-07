"""Stores and returns OAuth clients."""
import logging

from .OAuthServiceImpl import OAuthFlow

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

_clients = {}


def get_oauth_client(name) -> OAuthFlow:
    """Return an existing OAuth client or create a new one based on the name."""
    if name in _clients:
        return _clients[name]

    LOG.debug("Creating new OAuth client for '%s'", name)
    _clients[name] = OAuthFlow(name)
    return _clients[name]
