"""Provides configuration management for Sailor."""
from collections import namedtuple
from contextlib import contextmanager
import os
import logging
import json
import sys
import warnings

import yaml

from .utils import DataNotFoundWarning

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

CONFIG_PROPERTIES = ('asset_central', 'sap_iot')


@contextmanager
def try_log(exception, msg):
    """Run code in try-except clause, logs message when exception is called and re-raises exception."""
    try:
        yield
    except exception as exc:
        if hasattr(msg, "__call__"):
            msg = msg(exc)
        LOG.error(msg)
        raise


class SailorConfig(namedtuple('SailorConfig', CONFIG_PROPERTIES)):
    """Stores the config of Sailor."""

    config = None

    @staticmethod
    def get(*keys):
        """Return a value from the config.

        Supports deep lookup if values are dicts.

        Example
        -------
        >>> SailorConfig.get('asset_central', 'client_id')
        """
        if SailorConfig.config is None:
            SailorConfig.load()
        res = getattr(SailorConfig.config, keys[0])
        for k in keys[1:]:
            res = res[k]
        return res

    @staticmethod
    def load():
        """Load config of Sailor from environment or YAML file.

        Tries environment first, then YAML file.
        If there is an error during one attempt the load will fail (no further methods will be tried).

        Returns
        -------
        SailorConfig
            The loaded config. If load() was called before, returns cached config.
        """
        if SailorConfig.config is not None:
            LOG.debug('config already loaded. returning cached config')
            return SailorConfig.config

        SailorConfig.config = SailorConfig._load()
        _configure_sailor()
        return SailorConfig.config

    @staticmethod
    def _load():
        """Load config from ENV or YAML file."""
        if os.getenv('SAILOR_CONFIG_JSON') is None:
            LOG.debug('SAILOR_CONFIG_JSON not found in env. skipping config load from env.')
        else:
            LOG.debug('found SAILOR_CONFIG_JSON in env. trying to load config from env.')
            with try_log(Exception, 'Error while loading the configuration from SAILOR_CONFIG_JSON.'):
                SailorConfig.config = SailorConfig.from_env()
            LOG.info('Successfully loaded config from environment.')
            return SailorConfig.config

        yaml_paths = [os.getenv('SAILOR_CONFIG_PATH', os.path.join(os.path.abspath(os.curdir), 'config.yml')),
                      os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'config.yml')]
        yaml_paths = [p for p in yaml_paths if os.path.exists(p)]
        try:
            yaml_config_path = yaml_paths[0]
        except IndexError:
            LOG.debug('no config YAML file found. skipping YAML file load.')
        else:
            LOG.debug('found config file at %s. trying YAML load', yaml_config_path)
            with try_log(Exception, f'Error while loading the configuration from YAML file at {yaml_config_path}.'):
                SailorConfig.config = SailorConfig.from_yaml(yaml_config_path)
            LOG.info('Successfully loaded config from YAML file.')
            return SailorConfig.config

        raise RuntimeError('No methods left for loading the config.')

    @classmethod
    def from_env(cls):
        """Load config from environment.

        Uses ``SAILOR_CONFIG_JSON`` in environment. Value needs to be JSON encoded.
        """
        config_dict = json.loads(os.environ['SAILOR_CONFIG_JSON'])
        with try_log(TypeError, lambda e: 'Missing configuration parameter(s): %s' % str(e)[str(e).find(':')+2:]):
            return cls(**config_dict)

    @classmethod
    def from_yaml(cls, path):
        """Load config from YAML file."""
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
        with try_log(TypeError, lambda e: 'Missing configuration parameter(s): %s' % str(e)[str(e).find(':')+2:]):
            return cls(**config_dict)


def _configure_sailor():
    warnings.filterwarnings("always", category=DataNotFoundWarning,
                            append=True)  # simpler for the user to override this setting
