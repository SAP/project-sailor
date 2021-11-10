"""Improvements to OAuth and OData clients."""
import logging
import json
import warnings
from datetime import datetime, timezone
import time

from furl import furl
from rauth import OAuth2Service
import jwt

from ..config import SailorConfig
from .scope_config import SCOPE_CONFIG

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


class OAuth2Client():
    """Provide session management for OAuth2 enhanced requests :class:`~requests.sessions.Session`'s.

    Manages a single session that can be used for making requests against endpoints which accept tokens issued by
    the auth server used by this client.

    Single entrypoint should be the convenience :meth:`request` method which acts as a convenience method for making
    OAuth2 enhanced HTTP requests with an instance of this class.
    """

    def __init__(self, name, scope_config=None):
        """
        Create a OAuth2Client.

        :param name: name of the OAuth2Client. Must be a service name found in the SailorConfig.
        :param scope_config: restrict access for this instance to certain scopes listed in scope_config
        """
        self.name = name
        self.client_id = SailorConfig.get(name, 'client_id')
        self.client_secret = SailorConfig.get(name, 'client_secret')
        self.access_token_url = SailorConfig.get(name, 'access_token_url')
        self.subdomain = SailorConfig.get(name, 'subdomain')
        if 'https://' in self.access_token_url:
            self.oauth_url = 'https://' + self.subdomain + '.' + self.access_token_url[len('https://'):]
        else:
            self.oauth_url = 'https://' + self.subdomain + '.' + self.access_token_url

        scope_config = SCOPE_CONFIG if scope_config is None else scope_config
        self.configured_scopes = scope_config.get(self.name, [])
        self.resolved_scopes = []
        self._active_session = None

    def request(self, method, url, **req_kwargs):
        """Make a request using this convenience wrapper.

        The interface is the same as the :meth:`requests.sessions.Session.request` method provides but changes the
        following behavior:

        - Does not return a response object. Instead, returns content or raises an error (see below).
        - Automatically converts supplied 'params' for GET requests to OData URL parameters.
        - If headers are not set, requests for JSON content by default.

        Client session management: will use the currently attached session with this client or create a new one.
        If scopes are configured with this client and are not resolved yet, will try to resolve the scopes with
        the auth server first before making the request.

        Returns
        -------
        A dict if the response contains JSON. Otherwise returns the response content as bytes.

        Raises
        ------
        RequestError
            When the reponse is retrieved but response code is 400 or higher.
        """
        if method == 'GET':
            parameters = req_kwargs.pop('params', {})
            url_obj = furl(url)
            url_obj.args = {**url_obj.args, **parameters}
            url = url_obj.tostr(query_quote_plus=False)

        req_kwargs.setdefault('headers', {'Accept': 'application/json'})

        if self.configured_scopes and not self.resolved_scopes:
            try:
                self._resolve_configured_scopes()
            except Exception as exc:
                warnings.warn('Could not resolve the configured scopes. Trying to continue without scopes...')
                LOG.debug(exc, exc_info=True)

        scope = ' '.join(self.resolved_scopes) if self.resolved_scopes else None
        session = self._get_session(scope=scope)

        LOG.debug('Calling %s with req_kwargs: %s', url, req_kwargs)
        response = session.request(method, url, **req_kwargs)
        if response.ok:
            if response.headers.get('content-type', '').lower() == 'application/json':
                # TODO: remove this workaround when API has been fixed
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return response.content
            else:
                return response.content
        else:
            msg = f'Request failed. Response {response.status_code} ({response.reason}): {response.text}'
            raise RequestError(msg, response.status_code, response.reason, response.text)

    def _get_session(self, scope=None):
        """
        Return the current active session or create a new one.

        If a session exists, check if the session is valid and return that session.
        Otherwise create a new session.
        """
        if self._active_session:
            use_active_session = True
            decoded_token = jwt.decode(self._active_session.access_token_response.json()['access_token'],
                                       options={'verify_signature': False})
            expiration_time = decoded_token['exp']
            if expiration_time - time.time() < 5*60:
                LOG.debug('OAuth session expires at %s', datetime.fromtimestamp(expiration_time, tz=timezone.utc))
                use_active_session = False
            elif scope is not None:
                if sorted(decoded_token['scope']) != sorted(scope.split(' ')):
                    use_active_session = False
                    LOG.debug('Scopes are not identical.')

            if use_active_session:
                return self._active_session
            else:
                try:
                    self._active_session.close()
                except Exception:
                    LOG.exception('Could not close OAuth2Session.')

        LOG.debug('Creating new OAuth session for "%s"', self.name)
        params = {'grant_type': 'client_credentials', 'scope': scope}
        service = OAuth2Service(name=self.name, client_id=self.client_id, client_secret=self.client_secret,
                                access_token_url=self.oauth_url)

        try:
            self._active_session = service.get_auth_session('POST', data=params, decoder=json.loads)
        except json.JSONDecodeError as exception:
            LOG.debug('Decoding JSON while getting auth session failed.', exc_info=exception)
            raise RuntimeError('Decoding JSON while getting auth session failed. Original content: \n' + exception.doc)

        # the get_auth_session method of rauth does not check whether the response was 200 or not
        # and therefore does not log a proper error message
        if self._active_session.access_token_response.ok:
            return self._active_session
        else:
            self._active_session = None
            raise RuntimeError('get_auth_session call did not receive a successful token response.')

    def _resolve_configured_scopes(self):
        """
        Resolve oauth scopes based on initialized scope config.

        Involves a remote call to fetch the auth token.
        Resolved scopes will be stored in `self.resolved_scopes`.
        If no scopes are configured then calling this method has no effect.

        Returns: None
        """
        if not self.configured_scopes:
            return

        encoded_token = self._get_session().access_token_response.json()['access_token']
        decoded_token = jwt.decode(encoded_token, options={'verify_signature': False})
        all_scopes = decoded_token['scope']

        resolved_scopes = []
        missing_corresponding_scopes = []

        for short_scope in self.configured_scopes:
            matches = [scope for scope in all_scopes if scope.endswith(short_scope)]

            if len(matches) >= 1:
                # assumption:
                # when there are multiple prefixed scopes for the given
                # unprefixed scope we take the first match only
                resolved_scopes.append(matches[0])
            else:
                missing_corresponding_scopes.append(repr(short_scope))

        # assumption:
        # we consider the scope configuration invalid when at least one
        # corresponding prefixed scope from auth token is absent
        if missing_corresponding_scopes:
            warnings.warn('Could not resolve all scopes. Scope configuration considered invalid. ' +
                          f'Continuing without resolved scopes. Missing scopes: {missing_corresponding_scopes}.')
            self.resolved_scopes = []
        else:
            self.resolved_scopes = resolved_scopes


class RequestError(Exception):
    """Exception object with additional information about the status returned by a REST request."""

    def __init__(self, msg, status_code, reason, error_text):
        super().__init__(msg)
        self.status_code = status_code
        self.reason = reason
        self.error_text = error_text
