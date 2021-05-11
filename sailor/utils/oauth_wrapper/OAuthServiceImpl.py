"""Contains the OAuthFlow class which simplifies the interaction with OAuth-based APIs."""
import json
import logging
import warnings
from datetime import datetime, timezone
import time

import jwt
from furl import furl
from rauth import OAuth2Service

from ..config import SailorConfig
from .scope_config import SCOPE_CONFIG

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


class OAuthFlow:
    """Provides methods for client_credential grant flows.

    This class acts as a wrapper for OAuth2Service class. On creating an object of this class, an instance of the
    OAuth2Service is created with the values provided.
    """

    def __init__(self, name, scope_config=SCOPE_CONFIG):
        """
        Create a OAuthFlow object.

        :param name: name of the OAuthFlow. Must be a service name found in the SailorConfig.
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

        self.configured_scopes = scope_config.get(self.name, [])
        self.resolved_scopes = []
        self._active_session = None

    def fetch_endpoint_data(self, endpoint_url, method, parameters=None):
        """
        Send request and return a JSON object from the obtained result.

        This method fetches the data on the endpoint_url specified as a parameter.
        There is no need to explicitly create an access_token and then request the data.
        If the endpoint_url already contains parameters, then these are extended by `parameters`.

        :param endpoint_url: A url which would fetch the data.
        :type endpoint_url: str
        :param method: Specifies the HTTP method
        :type method: str
        :param parameters: Set of parameters that needs to be send along with the request.
        :type parameters: dict
        """
        if self.configured_scopes and not self.resolved_scopes:
            try:
                self._resolve_configured_scopes()
            except Exception as exc:
                warnings.warn('Could not resolve the configured scopes. Trying to continue without scopes...')
                LOG.debug(exc, exc_info=True)

        oauth_params = {'scope': ' '.join(self.resolved_scopes)} if self.resolved_scopes else None
        session = self._get_session(oauth_params)

        if not parameters:
            parameters = {}

        parameters['$format'] = 'json'
        endpoint_url = furl(endpoint_url)
        endpoint_url.args = {**endpoint_url.args, **parameters}
        endpoint_url = endpoint_url.tostr(query_quote_plus=False)

        LOG.debug('Calling %s', endpoint_url)
        response = session.request(method, endpoint_url)
        if response.ok:
            if response.headers['Content-Type'] == 'application/json':
                return response.json()
            else:
                return response.content
        else:
            msg = f'Request failed. Response {response.status_code} ({response.reason}): {response.text}'
            LOG.error(msg)
            raise RequestError(msg, response.status_code, response.reason, response.text)

    def _get_session(self, params=None):
        """
        Return the current active session or create a new one.

        If a session exists, check if the session is valid and return that session.
        Otherwise create a new session with client_credentials grant by default.
        """
        if self._active_session:
            use_active_session = True
            decoded_token = jwt.decode(self._active_session.access_token_response.json()['access_token'],
                                       options={'verify_signature': False})
            expiration_time = decoded_token['exp']
            if expiration_time - time.time() < 5*60:
                LOG.debug('OAuth session expires at %s', datetime.fromtimestamp(expiration_time, tz=timezone.utc))
                use_active_session = False
            elif params is not None and 'scope' in params:
                if sorted(decoded_token['scope']) != sorted(params['scope'].split(' ')):
                    use_active_session = False
                    LOG.debug('Scopes are not identical.')
            elif params is not None and 'grant_type' in params:
                if params['grant_type'] != decoded_token['grant_type']:
                    use_active_session = False
                    LOG.debug('grant_types are not identical.')
            if use_active_session:
                return self._active_session

        LOG.debug('Creating new OAuth session for "%s"', self.name)
        if not params:
            params = {}
        params.setdefault('grant_type', 'client_credentials')
        service = OAuth2Service(name=self.name, client_id=self.client_id, client_secret=self.client_secret,
                                access_token_url=self.oauth_url)
        self._active_session = service.get_auth_session('POST', data=params, decoder=json.loads)

        # the get_auth_session method of rauth does not check whether the response was 200 or not
        # and therefore does not log a proper error message
        if self._active_session.access_token_response.ok:
            self._active_session.headers = {'Accept': 'application/json'}
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
