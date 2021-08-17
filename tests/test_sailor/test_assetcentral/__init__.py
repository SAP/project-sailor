import pkgutil
import os
import importlib

# make sure all assetcentral modules are imported before the tests are run
# otherwise the utils tests for AssetcentralEntityCollection relying on __subclasses__ will not include all subclasses,
# and will depend on execution order of tests
path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'sailor', 'assetcentral')
for importer, package_name, _ in pkgutil.iter_modules([path]):
    module = importlib.import_module('sailor.assetcentral.' + package_name)
