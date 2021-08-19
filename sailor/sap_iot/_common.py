import string

from cachetools.func import ttl_cache

from ..utils.config import SailorConfig
from ..utils.oauth_wrapper import get_oauth_client


class _CustomFormatter(string.Formatter):
    # Since the URL returned by the extension service contains the same format string key twice
    # this formatter can be used to fill those sequentially from an iterable
    def get_value(self, key, args, kwargs):
        return kwargs['replace'].pop(0)


@ttl_cache(maxsize=8, ttl=600)
def _request_extension_url(service, schema):
    """
    Parse the IoT extension metadata endpoint for the ASSETCNTRL schema.

    This function can be used to determine the correct endpoints for various SAP IoT extension services.
    Implemented using a TTLCache as not every request to find an extension URL should trigger a remote call for the
    metadata. The TTL cache is populated on the first call to determine an extension URL and then refreshed
    every 10 minutes. We decided not to populate the cache on application startup to avoid any potential errors being
    propagated to users who don't actually need any extension services.
    Unfortunately the extension metadata API does not provide any keys to identify the different services, so we
    need to match the correct service based on the service description.
    This is currently hard-coded to the ASSETCNTRL schema of SAP IoT, because we don't know any other schemas yet.
    If we need access to other schemas in the future I expect this functionality to become generic.
    """
    service_description_map = {
        'upload': 'Write time-series data',
        'read_aggregates': 'Read time-series analytics aggregates'
    }

    extension_service_url = SailorConfig.get('sap_iot', 'extension_url')
    oauth_iot = get_oauth_client('sap_iot')
    extension_config = oauth_iot.request('GET', f'{extension_service_url}/Extensions?schemaId={schema}')
    for entry in extension_config['Extensions']:
        if entry['Description'] == service_description_map[service]:  # there is no key, we have to match on description
            return entry['Service URL']

    raise RuntimeError(f'Could not find extension url for service {service} with description '
                       f'{service_description_map[service]}')


def request_upload_url(equipment_id, schema='ASSETCNTRL'):
    """Return the correctly formatted URL for uploading timeseries data for the specified equipment."""
    fmt = _CustomFormatter()
    url = _request_extension_url('upload', schema)
    return fmt.format(url, replace=[equipment_id])


def request_aggregates_url(indicator_group_id, start_timestamp, end_timestamp, schema='ASSETCNTRL'):
    """Return the correctly formatted URL for downloading aggregate timeseries data."""
    fmt = _CustomFormatter()

    url = _request_extension_url('read_aggregates', schema)
    return fmt.format(url, replace=[indicator_group_id, start_timestamp, end_timestamp])
