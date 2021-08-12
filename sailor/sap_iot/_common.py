from ..utils.config import SailorConfig
from ..utils.oauth_wrapper import get_oauth_client

__CACHED_EXTENSION_URLS = {}


def _populate_cache():
    extension_service_url = SailorConfig.get('sap_iot', 'extension_url')
    oauth_iot = get_oauth_client('sap_iot')
    extension_config = oauth_iot.request('GET', f'{extension_service_url}/Extensions?schemaId=ASSETCNTRL')
    for entry in extension_config['Extensions']:
        if entry['Description'] == 'Write time-series data':  # there is no key, we have to match on description
            __CACHED_EXTENSION_URLS['upload'] = entry['Service URL']
        if entry['Description'] == 'Read time-series analytics aggregates':
            __CACHED_EXTENSION_URLS['read_aggregates'] = entry['Service URL']


def format_upload_url(equipment_id):
    if 'upload' not in __CACHED_EXTENSION_URLS:
        _populate_cache()

    url = __CACHED_EXTENSION_URLS['upload']
    return url.format(ID=equipment_id)


def format_aggregates_url(indicator_group_id, start_timestamp, end_timestamp):
    if 'read_aggregates' not in __CACHED_EXTENSION_URLS:
        _populate_cache()

    url = __CACHED_EXTENSION_URLS['read_aggregates']
    return url.format(indicator_group_id, start_timestamp, end_timestamp)
