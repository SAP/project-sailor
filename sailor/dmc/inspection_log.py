"""
Inspection Log module can be used to retrieve Inspection Log information from Digital Manufacturing Cloud.

Classes are provided for individual Inspection Logs as well as groups of Inspection Logs (InspectionLogSet).
"""
from base64 import b64decode
from typing import Dict, Tuple
from functools import cached_property
import hashlib
import warnings

import pandas as pd

from sailor import _base
from sailor.utils.oauth_wrapper import RequestError
from sailor.utils.timestamps import _string_to_timestamp_parser
from .constants import AIML_GROUP, INSPECTION_LOG, INSPECTION_LOGS_FOR_CONTEXT
from .utils import (DigitalManufacturingCloudEntity, DigitalManufacturingCloudEntitySet,
                    _DigitalManufacturingCloudField, _dmc_application_url, _dmc_fetch_data)

_INSPECTION_LOG_FIELDS = [
    _DigitalManufacturingCloudField('file_id', 'fileId'),
    _DigitalManufacturingCloudField('timestamp', 'inspectionLogTime', get_extractor=_string_to_timestamp_parser()),
    _DigitalManufacturingCloudField('type', 'inspectionType'),
    _DigitalManufacturingCloudField('logged_nc_code', 'loggedNCCode'),
    _DigitalManufacturingCloudField('predicted_nc_code', 'predictedNCCode'),
    _DigitalManufacturingCloudField('is_conformant', 'isConformant'),
    _DigitalManufacturingCloudField('logged_nc_details', 'loggedNCS'),
    _DigitalManufacturingCloudField('predicted_nc_details', 'predictions'),
    _DigitalManufacturingCloudField('sfc', 'sfcId'),
    _DigitalManufacturingCloudField('material', 'material'),
    _DigitalManufacturingCloudField('operation', 'operation'),
    _DigitalManufacturingCloudField('plant', 'plant'),
    _DigitalManufacturingCloudField('resource', 'resource'),
    _DigitalManufacturingCloudField('routing', 'routing'),
    _DigitalManufacturingCloudField('source', 'source'),
    _DigitalManufacturingCloudField('view_name', 'inspectionViewName'),
    # _DigitalManufacturingCloudField('logged_annotation', 'loggedAnnotation'),
    # _DigitalManufacturingCloudField('predicted_annotation', 'predictedAnnotation'),
    # _DigitalManufacturingCloudField('predicted_class', 'predictedClass')
]

# all fields which can be used as request parameters for the endpoint /inspectionLogsForContext
_INSPECTION_LOG_FILTER_FIELDS = {
    'file_id': 'fileID',
    'from_date': 'fromDate',
    'to_date': 'toDate',
    'inspection_view_name': 'inspectionViewName',
    'logged_nc_code': 'loggedNCCode',
    'material': 'material',
    'operation': 'operation',
    'plant': 'plant',
    'resource': 'resource',
    'routing': 'routing',
    'scenario_id': 'scenarioID',
    'scenario_version': 'scenarioVersion',
    'sfc': 'sfc',
    'skip': 'skip',
    'source': 'source',
    'top': 'top',
    'timestamp': 'inspectionLogTime',
}


@_base.add_properties
class InspectionLog(DigitalManufacturingCloudEntity):
    """Digital Manufacturing Cloud InspectionLog Object."""

    _field_map = {field.our_name: field for field in _INSPECTION_LOG_FIELDS}

    @property
    def id(self):
        """Return the local replacement unique id of the InspectionLog."""
        return self._unique_id

    @cached_property
    def _unique_id(self):
        m = hashlib.sha256()
        unique_string = self.plant + self.sfc + self.view_name + self.file_id + self.raw['inspectionLogTime']
        m.update(unique_string.encode())
        return m.hexdigest()

    def _has_details(self):
        return any((key in self.raw for key in ['context', 'isConformant', 'loggedNCS', 'predictions', 'fileContent']))

    # TODO: Review whether to do some remapping to fit syntax with INSPECTION_LOG_FIELDS
    # or add the properties to the Inspection Logs returned by find_inspection_logs()
    def _get_details(self) -> None:
        """Fetch details about this specific Inspecton Log from Digital Manufacturing Cloud.

        Return the details, which contain more and easier to comprehend details on the inspection log, and, if
        applicable, the corresponding image as base64-encoded string.
        """
        endpoint_url = _dmc_application_url() + AIML_GROUP + INSPECTION_LOG

        # Material and operation might not be strictly necessary for identification of the correct Inspection Log,
        # however, if they are excluded the response will (or at the very least might) not contain any fileContent.
        params = {
            'timestamp': self.raw['inspectionLogTime'],
            'file_id': self.file_id,
            'plant': self.plant,
            'sfc': self.sfc,
            'material': self.material,
            'operation': self.operation,
        }

        try:
            # TODO: for some of the obviously existing inspectionlogs, this API says there is none
            response = _dmc_fetch_data(endpoint_url, params, _INSPECTION_LOG_FILTER_FIELDS)
        except RequestError as exc:
            if exc.status_code == 404:
                response = {}
            else:
                raise
        self.raw.update(response)


class InspectionLogSet(DigitalManufacturingCloudEntitySet):
    """Class representing a group of InspectionLogs."""

    _element_type = InspectionLog
    _images = None

    def __init__(self, elements):
        self._images = {}
        super().__init__(elements)

    def as_df(self, columns=None):
        if columns is None:
            columns = [field.our_name for field in self._element_type._field_map.values() if field.is_exposed]
        columns = columns + ['id']
        df = super().as_df(columns=columns)
        if 'is_conformant' in df.columns:
            df['is_conformant'] = df['is_conformant'].astype('boolean')
        return df

    @property
    def images(self):
        if not self._images:
            self._fetch_details_with_images()
        return self._images

    def _fetch_details_with_images(self):
        # the following code needs to be robust to multiple calls to this function because state is being modified
        # modified state (1): InspectionLog objects in the set are updated and base64 image data is dropped
        # modified state (2): self._images dict is updated with decoded image data
        no_content_file_ids = set()
        duplicate_file_ids = set()
        for inspection_log in self:
            if not inspection_log._has_details():
                inspection_log._get_details()

            file_id = inspection_log.raw['fileId']

            if 'fileContent' in inspection_log.raw:
                file_content = inspection_log.raw.pop('fileContent')
                if file_id not in self._images:
                    self._images[file_id] = b64decode(file_content)
                    if file_id in no_content_file_ids:
                        no_content_file_ids.remove(file_id)
                else:
                    duplicate_file_ids.add(file_id)
            else:
                if file_id not in self._images:
                    no_content_file_ids.add(file_id)
        if no_content_file_ids:
            warnings.warn(f"No file content available for files: {no_content_file_ids}.")
        if duplicate_file_ids:
            warnings.warn(("Multiple inspection logs found referring to the same file. "
                           "Only the first encountered file is stored. "
                           f"Affected files: {duplicate_file_ids}."))
            # TODO: we could also decide to overwrite the file, thus keeping only the last encountered occurrence

    def as_binary_classification_input(self, remove_duplicates=True) -> Tuple[pd.DataFrame, Dict[str, bytes]]:
        """Convert this `InspectionLogSet` to ML-Input for Binary Classification.

        Return a DataFrame containing the details of all Inspection Logs that contain an image and the
        isConformant-flag, and a dictionary mapping the bytes of those images to the corresponding fileId.
        """
        self._fetch_details_with_images()
        df = self.as_df()
        df = df.drop(columns=['logged_nc_code', 'predicted_nc_code', 'logged_nc_details', 'predicted_nc_details'])
        df = df[df['is_conformant'].notnull()]
        if remove_duplicates:
            df = _remove_duplicates(df)
        df, images = _remove_images_not_in_df_and_vice_versa(df, self._images)

        return df, images

    def as_multilabel_classification_input(self, remove_duplicates=True) -> Tuple[pd.DataFrame, Dict[str, bytes]]:
        """Convert this `InspectionLogSet` to ML-Input for Multi-label Classification.

        Return a DataFrame containing the details of all Inspection Logs that contain an image and either predictions
        or logged non-conformancies, and a dictionary mapping the bytes of those images to the corresponding fileId.
        """
        def has_items(list_):
            return False if list_ is None else len(list_) > 0

        self._fetch_details_with_images()
        df = self.as_df()
        df = df[df['logged_nc_details'].apply(has_items) | df['predicted_nc_details'].apply(has_items)]
        if remove_duplicates:
            df = _remove_duplicates(df)
        df, images = _remove_images_not_in_df_and_vice_versa(df, self._images)

        return df, images

    def as_object_detection_input(self, remove_duplicates=True) -> Tuple[pd.DataFrame, Dict[str, bytes]]:
        """Convert this `InspectionLogSet` to ML-Input for Object Detection.

        Return a DataFrame containing the details of all Inspection Logs that contain an image and whoose either
        predictions or logged non-conformancies countain bounding boxes, and a dictionary mapping the bytes of those
        images to the corresponding fileId. Removes all prediction/non-conformanicies without bounding boxes.
        """
        def has_items(list_):
            return False if list_ is None else len(list_) > 0

        def extract_bounding_boxes(list_):
            return [] if list_ is None else [item for item in list_
                                             if 'predictionBoundingBoxCoords' in item
                                             or 'defectBoundingBoxCoords' in item]

        self._fetch_details_with_images()
        df = self.as_df()
        df[['logged_nc_details', 'predicted_nc_details']] = \
            df[['logged_nc_details', 'predicted_nc_details']].applymap(extract_bounding_boxes)
        df = df[df['logged_nc_details'].apply(has_items) | df['predicted_nc_details'].apply(has_items)]
        if remove_duplicates:
            df = _remove_duplicates(df)
        df, images = _remove_images_not_in_df_and_vice_versa(df, self._images)

        return df, images

    def as_ml_input(self, remove_duplicates=True) -> Tuple[pd.DataFrame, Dict[str, bytes]]:
        """Convert this `InspectionLogSet` to generic ML-Input.

        Return a DataFrame containing the details of all Inspection Logs that contain an image and a dictionary
        mapping the bytes of those images to the corresponding fileId. Keeps the DataFrame generic in case the
        user wants to do their own data preparation.
        """
        self._fetch_details_with_images()
        df = self.as_df()
        if remove_duplicates:
            df = _remove_duplicates(df)
        df, images = _remove_images_not_in_df_and_vice_versa(df, self._images)
        return df, images


def find_inspection_logs(**kwargs) -> InspectionLogSet:
    """Fetch Inspection Logs from Digital Manufacturing Cloud with the applied filters, return an InspectionLogSet.

    Any named keyword arguments are applied as equality filters, i.e. the name of the InspectionLog property is checked
    against the value of the keyword argument. Arguments 'scenario_id' and 'scenario_version' are required.

    Parameters
    ----------
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Inspection Logs with scenario_id 'MyScenarioID' and scenario_version 1:

      find_inspection_logs(scenario_id='MyScenarioID', scenario_version=1)

    Find all Inspection Logs with scenario_id 'MyScenarioID', scenario_version 1 and Inspection
    Log Time 31.01.2021 08:30:00:000:

      kwargs = {
          'scenario_id': 'MyScenarioID',
          'scenario_version': 1,
          'timestamp': '2021-31-01 08:30:00:000',
      }

      find_inspection_logs(**kwargs)
    """
    if (not ('scenario_id' in kwargs.keys())) or (not ('scenario_version' in kwargs.keys())):
        raise ValueError('Please specify a scenario_id and a scenario_version.')

    endpoint_url = _dmc_application_url() + AIML_GROUP + INSPECTION_LOGS_FOR_CONTEXT

    object_list = _dmc_fetch_data(endpoint_url, kwargs, _INSPECTION_LOG_FILTER_FIELDS)

    return InspectionLogSet([InspectionLog(obj) for obj in object_list])


#
# helper functions
#
def _remove_duplicates(df):
    """Remove in respect to fileId duplicate Inspection Logs from DataFrame, keep only the most recent."""
    df = df.sort_values('timestamp', ascending=False)
    df = df.drop_duplicates(['file_id'])
    return df


def _remove_images_not_in_df_and_vice_versa(df, images):
    """Remove all images from the images-dict that do not have a label in the df and vice versa."""
    file_ids = set(df['file_id'].tolist()).intersection(images.keys())
    filtered_images = {file_id: images[file_id] for file_id in file_ids}
    df = df[df['file_id'].isin(file_ids)]
    return df, filtered_images
