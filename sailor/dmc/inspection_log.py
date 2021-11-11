"""
Inspection Log module can be used to retrieve Inspection Log information from Digital Manufacturing Cloud.

Classes are provided for individual Inspection Logs as well as groups of Inspection Logs (InspectionLogSet).
"""
from base64 import b64decode
from typing import Any, Dict, List, Tuple

import pandas as pd
from sailor import _base

from .constants import AIML_GROUP, INSPECTION_LOG, INSPECTION_LOGS_FOR_CONTEXT
from .utils import (DigitalManufacturingCloudEntity, DigitalManufacturingCloudEntitySet,
                    _DigitalManufacturingCloudField, _dmc_application_url, _dmc_fetch_data)

# TODO: replace inspectionLogTime by a more suitable id as soon as one is available via the API
_INSPECTION_LOG_FIELDS = [
    _DigitalManufacturingCloudField('file_id', 'fileId'),
    _DigitalManufacturingCloudField('id', 'inspectionLogTime'),
    _DigitalManufacturingCloudField('type', 'inspectionType'),
    _DigitalManufacturingCloudField('view_name', 'inspectionViewName'),
    _DigitalManufacturingCloudField('logged_annotation', 'loggedAnnotation'),
    _DigitalManufacturingCloudField('logged_nc_code', 'loggedNCCode'),
    _DigitalManufacturingCloudField('material', 'material'),
    _DigitalManufacturingCloudField('operation', 'operation'),
    _DigitalManufacturingCloudField('plant', 'plant'),
    _DigitalManufacturingCloudField('predicted_annotation', 'predictedAnnotation'),
    _DigitalManufacturingCloudField('predicted_class', 'predictedClass'),
    _DigitalManufacturingCloudField('predicted_nc_code', 'predictedNCCode'),
    _DigitalManufacturingCloudField('resource', 'resource'),
    _DigitalManufacturingCloudField('routing', 'routing'),
    _DigitalManufacturingCloudField('sfc', 'sfcId'),
    _DigitalManufacturingCloudField('source', 'source'),
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
    'id': 'inspectionLogTime',
}


@_base.add_properties
class InspectionLog(DigitalManufacturingCloudEntity):
    """Digital Manufacturing Cloud InspectionLog Object."""

    _field_map = {field.our_name: field for field in _INSPECTION_LOG_FIELDS}

    # TODO: Review whether to make this function private, do some remapping to fit syntax with INSPECTION_LOG_FIELDS
    # or add the properties to the Inspection Logs returned by find_inspection_logs()
    def _get_details(self) -> Dict[str, Any]:
        """Fetches details about this specific Inspecton Log and if applicable the corresponding image as
        base64-encoded string from Digital Manufacturing Cloud.
        """
        endpoint_url = _dmc_application_url() + AIML_GROUP + INSPECTION_LOG

        # Material and operation might not be strictly necessary for identification of the correct Inspection Log,
        # however, if they are excluded the response will (or at the very least might) not contain any fileContent.
        params = {
            'id': self.id,
            'file_id': self.file_id,
            'plant': self.plant,
            'sfc': self.sfc,
            'material': self.material,
            'operation': self.operation,
        }

        response = _dmc_fetch_data(endpoint_url, params, _INSPECTION_LOG_FILTER_FIELDS)

        return response


class InspectionLogSet(DigitalManufacturingCloudEntitySet):
    """Class representing a group of InspectionLogs."""

    _element_type = InspectionLog

    def _get_details_and_images(self) -> Tuple[List[Dict[str, Any]], Dict[str, bytes]]:
        """Fetches details with :ref:`_get_details()` and decodes the base64-encoded images to bytes.
        Returns a list containing all details for Inspection Logs containing images and a dict mapping bytes to fileId.
        """

        details = []
        images = {}

        for inspection_log in self.elements:

            inspection_log_details = inspection_log._get_details()

            if 'fileContent' not in inspection_log_details.keys():
                continue

            filename = inspection_log_details['fileId']

            image_bytes = b64decode(inspection_log_details['fileContent'])

            images[filename] = image_bytes

            inspection_log_details.pop('fileContent')

            details.append(inspection_log_details)

        return details, images

    def _remove_duplicates(self, df) -> pd.DataFrame:
        """Removes in respect to fileId duplicate Inspection Logs from DataFrame, keeping only the most recent."""
        df = df.sort_values('inspectionLogTime', ascending=False)
        df = df.drop_duplicates(['fileId'])
        return df

    def _remove_images_not_in_df(self, df, images) -> Dict[str, bytes]:
        """Removes all images from the images-dict that do not have a label in the df."""
        available_files = df['fileId'].tolist()
        filtered_images = {file_id: images[file_id] for file_id in available_files}
        return filtered_images

    def as_binary_classification_input(self, remove_duplicates=True):
        """Returns a DataFrame containing the details of all Inspection Logs that contain an image and the isConformant-flag,
        and a dictionary mapping the bytes of those images to the corresponding fileId."""
        details, images = self._get_details_and_images()

        df = pd.DataFrame()

        for details_item in details:
            if 'isConformant' not in details_item.keys():
                continue

            details_item.update(details_item['context'])
            details_item.pop('context')
            details_item.pop('fileID', None)

            details_item.pop('scenarioVersion', None)
            details_item.pop('scenarioId', None)

            details_item.pop('predictions', None)
            details_item.pop('loggedNCS', None)

            df = df.append(details_item, ignore_index=True)

        df['inspectionLogTime'] = pd.to_datetime(df['inspectionLogTime'])

        df['isConformant'] = df['isConformant'].astype('boolean')

        if remove_duplicates:
            df = self._remove_duplicates(df)

        images = self._remove_images_not_in_df(df, images)

        return df, images

    def as_multilabel_classification_input(self, remove_duplicates=True) -> Tuple[pd.DataFrame, Dict[str, bytes]]:
        """Returns a DataFrame containing the details of all Inspection Logs that contain an image and either predictions
        or logged non-conformancies, and a dictionary mapping the bytes of those images to the corresponding fileId."""
        details, images = self._get_details_and_images()

        df = pd.DataFrame()

        for details_item in details:
            if (len(details_item['predictions']) == 0) and (len(details_item['loggedNCS']) == 0):
                continue

            details_item.update(details_item['context'])
            details_item.pop('context')
            details_item.pop('fileID', None)

            details_item.pop('scenarioVersion', None)
            details_item.pop('scenarioId', None)

            df = df.append(details_item, ignore_index=True)

        df['inspectionLogTime'] = pd.to_datetime(df['inspectionLogTime'])

        df['isConformant'] = df['isConformant'].astype('boolean')

        if remove_duplicates:
            df = self._remove_duplicates(df)

        images = self._remove_images_not_in_df(df, images)

        return df, images

    def _contains_bounding_box(self, details_item) -> bool:
        """Looks into predictions and logged non-conformancies and return whether one of both
        contains a bounding box."""
        for prediction in details_item['predictions']:
            if 'predictionBoundingBoxCoords' in prediction.keys():
                if prediction['predictionBoundingBoxCoords'] != '[]':
                    return True

        for logged_ncs in details_item['loggedNCS']:
            if 'defectBoundingBoxCoords' in logged_ncs.keys():
                if logged_ncs['defectBoundingBoxCoords'] != '[]':
                    return True

        return False

    def as_object_detection_input(self, remove_duplicates=True) -> Tuple[pd.DataFrame, Dict[str, bytes]]:
        """Returns a DataFrame containing the details of all Inspection Logs that contain an image and whoose either
        predictions or logged non-conformancies countain bounding boxes, and a dictionary mapping the bytes of those
        images to the corresponding fileId. Removes all prediction/non-conformanicies without bounding boxes."""
        details, images = self._get_details_and_images()

        df = pd.DataFrame()

        for details_item in details:
            if not self._contains_bounding_box(details_item):
                continue

            details_item['predictions'] = [
                prediction for prediction in details_item['predictions']
                if 'predictionBoundingBoxCoords' in prediction.keys()
            ]

            details_item['loggedNCS'] = [
                prediction for prediction in details_item['loggedNCS']
                if 'defectBoundingBoxCoords' in prediction.keys()
            ]

            details_item.update(details_item['context'])
            details_item.pop('context')
            details_item.pop('fileID', None)

            details_item.pop('scenarioVersion', None)
            details_item.pop('scenarioId', None)

            df = df.append(details_item, ignore_index=True)

        df['inspectionLogTime'] = pd.to_datetime(df['inspectionLogTime'])

        df['isConformant'] = df['isConformant'].astype('boolean')

        if remove_duplicates:
            df = self._remove_duplicates(df)

        images = self._remove_images_not_in_df(df, images)

        return df, images

    def as_ml_input(self, remove_duplicates=True) -> Tuple[pd.DataFrame, Dict[str, bytes]]:
        """Returns a DataFrame containing the details of all Inspection Logs that contain an image and a dictionary
        mapping the bytes of those images to the corresponding fileId. Keeps the DataFrame generic in case the
        user wants to do their own data preparation."""
        details, images = self._get_details_and_images()

        df = pd.DataFrame()

        for details_item in details:
            details_item.update(details_item['context'])
            details_item.pop('context')
            details_item.pop('fileID', None)

            details_item.pop('scenarioVersion', None)
            details_item.pop('scenarioId', None)

            df = df.append(details_item, ignore_index=True)

        df['inspectionLogTime'] = pd.to_datetime(df['inspectionLogTime'])

        df['isConformant'] = df['isConformant'].astype('boolean')

        if remove_duplicates:
            df = self._remove_duplicates(df)

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
          'id': '2021-31-01 08:30:00:000',
      }

      find_inspection_logs(**kwargs)
    """
    if (not ('scenario_id' in kwargs.keys())) or (not ('scenario_version' in kwargs.keys())):
        raise ValueError('Please specify a scenario_id and a scenario_version.')

    endpoint_url = _dmc_application_url() + AIML_GROUP + INSPECTION_LOGS_FOR_CONTEXT

    object_list = _dmc_fetch_data(endpoint_url, kwargs, _INSPECTION_LOG_FILTER_FIELDS)

    return InspectionLogSet([InspectionLog(obj) for obj in object_list])
