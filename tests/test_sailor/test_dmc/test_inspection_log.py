from base64 import b64decode
from unittest.mock import call, patch
from copy import deepcopy

import pandas as pd
import pytest

from sailor.dmc.inspection_log import (InspectionLog, InspectionLogSet, find_inspection_logs)

_SCENARIO_ID = '123'
_SCENARIO_VERSION = 1
_FILE_1 = 'File1.png'
_FILE_2 = 'File2.png'
_TIME_1 = '2000-01-01 00:00:00.000'
_TIME_2 = '2000-01-02 00:00:00.000'
_TIME_3 = '2000-01-03 00:00:00.000'
# this is a dummy 1x1 pixel pink png since it has to be something base64-decodable
_FILE_1_CONTENT = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg=='
# this is a dummy 1x1 pixel green png since it has to be something base64-decodable
_FILE_2_CONTENT = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP0/M9QDwAEqgHJZfPahwAAAABJRU5ErkJggg=='
_FILE_CONTENT_TYPE = 'image/png'
_TYPE = 'Example_Type'
_PLANT = 'Example_Plant'
_MATERIAL = 'Example_Material'
_OPERATION = 'Example_Operation'
_RESOURCE = 'Example_Resource'
_ROUTING = 'Example_Routing'
_SFC = 'Example_SFC'
_SOURCE = 'Example_Source'
_VIEW_NAME = 'default'
_NC_1 = 'NC_1'
_NC_1_CLASS = 'NC_1_Class'
_NC_2 = 'NC_2'
_NC_2_CLASS = 'NC_2_Class'
_NC_3 = 'NC_3'
_NC_3_CLASS = 'NC_3_Class'

_BB_NC_1_LOG = '[{"type":"rect","x":0.8,"y":0.7,"w":0.1,"h":0.1,"score":0.99}]'
_BB_NC_1_PRED = '[{"type":"rect","x":0.8,"y":0.7,"w":0.1,"h":0.1,"score":0.95}]'
_BB_NC_3_LOG = '[{"type":"rect","x":0.4,"y":0.3,"w":0.4,"h":0.2,"score":0.85}]'
_BB_NC_3_PRED = '[{"type":"rect","x":0.4,"y":0.3,"w":0.4,"h":0.2,"score":0.89}]'

_MOCK_RESPONSE = [{
    'fileId': _FILE_1,
    'inspectionLogTime': _TIME_1,
    'inspectionType': _TYPE,
    'inspectionViewName': _VIEW_NAME,
    'loggedAnnotation': f'{_NC_1}:{_BB_NC_1_LOG};{_NC_3}:{_BB_NC_3_LOG}',
    'loggedNCCode': f'{_NC_1};{_NC_3}',
    'material': _MATERIAL,
    'operation': _OPERATION,
    'plant': _PLANT,
    'predictedAnnotation': f'{_NC_1}:{_BB_NC_1_PRED};{_NC_3}:{_BB_NC_3_PRED}',
    'predictedClass': f'{_NC_1_CLASS}:0.95;{_NC_3_CLASS}:0.89',
    'predictedNCCode': f'{_NC_1}:0-95;{_NC_3}:0.89',
    'resource': _RESOURCE,
    'routing': _ROUTING,
    'sfcId': _SFC,
    'source': _SOURCE,
}, {
    'fileId': _FILE_2,
    'inspectionLogTime': _TIME_2,
    'inspectionType': _TYPE,
    'inspectionViewName': _VIEW_NAME,
    'material': _MATERIAL,
    'operation': _OPERATION,
    'plant': _PLANT,
    'predictedAnnotation': f'{_NC_2}:[]',
    'predictedClass': f'{_NC_2_CLASS}:0.75',
    'predictedNCCode': f'{_NC_2}:0.75',
    'resource': _RESOURCE,
    'routing': _ROUTING,
    'sfcId': _SFC,
    'source': _SOURCE,
}, {
    'fileId': _FILE_2,
    'inspectionLogTime': _TIME_3,
    'inspectionType': _TYPE,
    'inspectionViewName': _VIEW_NAME,
    'material': _MATERIAL,
    'operation': _OPERATION,
    'plant': _PLANT,
    'resource': _RESOURCE,
    'routing': _ROUTING,
    'sfcId': _SFC,
    'source': _SOURCE,
}]

_DETAILS_1 = {
    'context': {
        'plant': _PLANT,
        'sfc': _SFC,
        'material': _MATERIAL,
        'operation': _OPERATION,
        'resource': _RESOURCE,
        'routing': _ROUTING,
        'source': _SOURCE,
        'inspectionViewName': _VIEW_NAME,
    },
    'fileContent': _FILE_1_CONTENT,
    'fileContentType': _FILE_CONTENT_TYPE,
    'fileId': _FILE_1,
    'inspectionLogTime': _TIME_1,
    'isConformant': False,
    'loggedNCS': [{
        'defectBoundingBoxCoords': _BB_NC_1_LOG,
        'ncCode': _NC_1,
    }, {
        'defectBoundingBoxCoords': _BB_NC_3_LOG,
        'ncCode': _NC_3,
    }],
    'predictions': [{
        'ncCode': _NC_1,
        'predictionBoundingBoxCoords': _BB_NC_1_PRED,
        'predictionClass': _NC_1_CLASS,
        'predictionScore': 0.95,
    }, {
        'ncCode': _NC_3,
        'predictionBoundingBoxCoords': _BB_NC_3_PRED,
        'predictionClass': _NC_3_CLASS,
        'predictionScore': 0.89,
    }],
    'scenarioID': _SCENARIO_ID,
    'scenarioVersion': _SCENARIO_VERSION,
}

_DETAILS_2 = {
    'context': {
        'plant': _PLANT,
        'sfc': _SFC,
        'material': _MATERIAL,
        'operation': _OPERATION,
        'resource': _RESOURCE,
        'routing': _ROUTING,
        'source': _SOURCE,
        'inspectionViewName': _VIEW_NAME,
    },
    'fileContent': _FILE_2_CONTENT,
    'fileContentType': _FILE_CONTENT_TYPE,
    'fileId': _FILE_2,
    'inspectionLogTime': _TIME_2,
    'loggedNCS': [],
    'predictions': [{
        'isLogged': False,
        'ncCode': _NC_2,
        'predictionClass': _NC_2_CLASS,
        'predictionScore': 0.75,
    }],
    'scenarioID': _SCENARIO_ID,
    'scenarioVersion': _SCENARIO_VERSION,
}

_DETAILS_3 = {
    'context': {
        'plant': _PLANT,
        'sfc': _SFC,
        'material': _MATERIAL,
        'operation': _OPERATION,
        'resource': _RESOURCE,
        'routing': _ROUTING,
        'source': _SOURCE,
        'inspectionViewName': _VIEW_NAME,
    },
    'fileContent': _FILE_2_CONTENT,
    'fileContentType': _FILE_CONTENT_TYPE,
    'fileId': _FILE_2,
    'inspectionLogTime': _TIME_3,
    'isConformant': True,
    'loggedNCS': [],
    'predictions': [],
    'scenarioID': _SCENARIO_ID,
    'scenarioVersion': _SCENARIO_VERSION,
}


@pytest.fixture
def mock_url():
    with patch('sailor.dmc.inspection_log._dmc_application_url') as mock:
        mock.return_value = 'base_url'
        yield mock


@pytest.fixture
def mock_fetch():
    with patch('sailor.dmc.inspection_log._dmc_fetch_data') as mock:
        yield mock


def test_expected_public_attributes_are_present():
    expected_attributes = [
        'file_id', 'timestamp', 'type', 'logged_nc_code', 'predicted_nc_code', 'is_conformant', 'logged_nc_details',
        'predicted_nc_details', 'sfc', 'material', 'operation', 'plant', 'resource', 'routing', 'source', 'view_name',
    ]

    fieldmap_public_attributes = [field.our_name for field in InspectionLog._field_map.values() if field.is_exposed]

    assert expected_attributes == fieldmap_public_attributes
    assert InspectionLog.id is not None


def test_find_inspection_logs_correct_arguments(mock_url, mock_fetch):

    scenario_id = '123'
    scenario_version = 1

    expected_url = 'base_url/aiml/v1/inspectionLogsForContext'

    expected_filters = {
        'scenario_id': '123',
        'scenario_version': 1,
    }

    expected_filter_fields = {
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

    find_inspection_logs(scenario_id=scenario_id, scenario_version=scenario_version)

    mock_fetch.assert_called_once_with(expected_url, expected_filters, expected_filter_fields)


def test_find_inspection_logs_raises_error_if_scenario_id_or_version_missing(mock_url, mock_fetch):

    scenario_id = '123'
    scenario_version = 1

    with pytest.raises(ValueError, match='Please specify a scenario_id and a scenario_version.'):
        find_inspection_logs(scenario_id=scenario_id)

    with pytest.raises(ValueError, match='Please specify a scenario_id and a scenario_version.'):
        find_inspection_logs(scenario_version=scenario_version)


def test_find_inspection_logs_result(mock_url, mock_fetch):
    kwargs = {
        'scenario_id': '123',
        'scenario_version': 1,
    }
    mock_fetch.return_value = deepcopy(_MOCK_RESPONSE)
    expected_result = InspectionLogSet([InspectionLog(result) for result in deepcopy(_MOCK_RESPONSE)])

    actual = find_inspection_logs(**kwargs)

    assert type(actual) == InspectionLogSet
    assert expected_result == actual


def test_inspection_log_constructs_correct_object():
    expected_attributes = {
        'file_id': _FILE_1,
        'timestamp': pd.Timestamp(_TIME_1, tz='UTC'),
        'type': _TYPE,
        'view_name': _VIEW_NAME,
        #'logged_annotation': f'{_NC_1}:{_BB_NC_1_LOG};{_NC_3}:{_BB_NC_3_LOG}',
        'logged_nc_code': f'{_NC_1};{_NC_3}',
        'material': _MATERIAL,
        'operation': _OPERATION,
        'plant': _PLANT,
        #'predicted_annotation': f'{_NC_1}:{_BB_NC_1_PRED};{_NC_3}:{_BB_NC_3_PRED}',
        #'predicted_class': f'{_NC_1_CLASS}:0.95;{_NC_3_CLASS}:0.89',
        'predicted_nc_code': f'{_NC_1}:0-95;{_NC_3}:0.89',
        'resource': _RESOURCE,
        'routing': _ROUTING,
        'sfc': _SFC,
        'source': _SOURCE
    }
    actual = InspectionLog(_MOCK_RESPONSE[0])

    for property_name, value in expected_attributes.items():
        assert getattr(actual, property_name) == value


def test_get_details(mock_url, mock_fetch):
    inspection_log = InspectionLog({
        'fileId': _FILE_1,
        'inspectionLogTime': _TIME_1,
        'inspectionType': _TYPE,
        'inspectionViewName': _VIEW_NAME,
        'loggedAnnotation': f'{_NC_1}:{_BB_NC_1_LOG};{_NC_3}:{_BB_NC_3_LOG}',
        'loggedNCCode': f'{_NC_1};{_NC_3}',
        'material': _MATERIAL,
        'operation': _OPERATION,
        'plant': _PLANT,
        'predictedAnnotation': f'{_NC_1}:{_BB_NC_1_PRED};{_NC_3}:{_BB_NC_3_PRED}',
        'predictedClass': f'{_NC_1_CLASS}:0.95;{_NC_3_CLASS}:0.89',
        'predictedNCCode': f'{_NC_1}:0-95;{_NC_3}:0.89',
        'resource': _RESOURCE,
        'routing': _ROUTING,
        'sfcId': _SFC,
        'source': _SOURCE})
    expected_url_log = 'base_url/aiml/v1/inspectionLog'
    expected_filters_log = {
        'timestamp': _TIME_1,
        'file_id': _FILE_1,
        'plant': _PLANT,
        'sfc': _SFC,
        'material': _MATERIAL,
        'operation': _OPERATION,
    }
    expected_filter_fields = {
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
    mock_fetch.return_value = deepcopy(_DETAILS_1)
    expected = deepcopy(inspection_log.raw)
    expected.update(_DETAILS_1)

    inspection_log._get_details()

    assert inspection_log.raw == expected
    mock_fetch.assert_has_calls([
        call(expected_url_log, expected_filters_log, expected_filter_fields),
    ])


@pytest.mark.filterwarnings('ignore:No file content available for files')
@pytest.mark.filterwarnings('ignore:Multiple inspection logs found referring to the same file.')
def test_fetch_details_with_images(mock_url, mock_fetch):
    details_list = [deepcopy(_DETAILS_1), deepcopy(_DETAILS_2), deepcopy(_DETAILS_3)]
    mock_fetch.side_effect = details_list   # _fetch_details_with_images calls

    # constructing it like this because of keeping the order
    inspection_logs = InspectionLogSet([])
    inspection_logs.elements = [InspectionLog(response) for response in deepcopy(_MOCK_RESPONSE)]

    file_1_decoded = b64decode(_FILE_1_CONTENT)
    file_2_decoded = b64decode(_FILE_2_CONTENT)

    expected_raw_list = deepcopy(_MOCK_RESPONSE)
    for i, detail in enumerate(details_list):
        expected_raw_list[i].update(detail)
        expected_raw_list[i].pop('fileContent')

    inspection_logs._fetch_details_with_images()

    for i, log in enumerate(inspection_logs):
        assert log.raw == expected_raw_list[i]
    assert len(inspection_logs.images) == 2
    assert inspection_logs.images[_FILE_1] == file_1_decoded
    assert inspection_logs.images[_FILE_2] == file_2_decoded


def test_fetch_details_with_images_warns_missing_file_content(mock_url, mock_fetch):
    # constructing it like this because of keeping the order
    inspection_logs = InspectionLogSet([])
    inspection_logs.elements = [InspectionLog(response) for response in deepcopy(_MOCK_RESPONSE)]

    details_list = [deepcopy(_DETAILS_1), deepcopy(_DETAILS_2), deepcopy(_DETAILS_3)]
    details_list[0].pop('fileContent')
    mock_fetch.side_effect = details_list

    with pytest.warns(UserWarning, match="No file content available for files: .*{'File1.png'}.*"):
        inspection_logs._fetch_details_with_images()


@pytest.mark.filterwarnings('ignore:No file content available for files')
@pytest.mark.filterwarnings('ignore:Multiple inspection logs found referring to the same file.')
def test_as_ml_input(mock_url, mock_fetch):
    inspection_logs = InspectionLogSet([])
    inspection_logs.elements = [InspectionLog(response) for response in deepcopy(_MOCK_RESPONSE)]

    details_list = [deepcopy(_DETAILS_1), deepcopy(_DETAILS_2), deepcopy(_DETAILS_3)]
    mock_fetch.side_effect = details_list

    df, images = inspection_logs.as_ml_input()

    assert len(df) == 2
    assert len(images) == 2

    expected_columns = [
        'file_id', 'timestamp', 'type', 'logged_nc_code', 'predicted_nc_code', 'is_conformant', 'logged_nc_details',
        'predicted_nc_details', 'sfc', 'material', 'operation', 'plant', 'resource', 'routing', 'source', 'view_name',
        'id'
    ]

    expected_timestamps = pd.to_datetime(pd.Series([_TIME_1, _TIME_3]), utc=True).to_list()
    unexpected_timestamps = pd.to_datetime(pd.Series([_TIME_2]), utc=True).to_list()
    actual_timestamps = df['timestamp'].to_list()

    assert sorted(expected_columns) == sorted(df.columns.to_list())

    assert sorted(expected_timestamps) == sorted(actual_timestamps)

    for ts in unexpected_timestamps:
        assert ts not in actual_timestamps

    expected_images = {
        _FILE_1: b64decode(_FILE_1_CONTENT),
        _FILE_2: b64decode(_FILE_2_CONTENT),
    }

    assert images == expected_images


@pytest.mark.filterwarnings('ignore:No file content available for files')
@pytest.mark.filterwarnings('ignore:Multiple inspection logs found referring to the same file.')
def test_as_ml_input_with_duplicates(mock_url, mock_fetch):
    inspection_logs = InspectionLogSet([])
    inspection_logs.elements = [InspectionLog(response) for response in deepcopy(_MOCK_RESPONSE)]

    details_list = [deepcopy(_DETAILS_1), deepcopy(_DETAILS_2), deepcopy(_DETAILS_3)]
    mock_fetch.side_effect = details_list

    df, images = inspection_logs.as_ml_input(remove_duplicates=False)

    assert len(df) == 3
    assert len(images) == 2

    expected_columns = [
        'file_id', 'timestamp', 'type', 'logged_nc_code', 'predicted_nc_code', 'is_conformant', 'logged_nc_details',
        'predicted_nc_details', 'sfc', 'material', 'operation', 'plant', 'resource', 'routing', 'source', 'view_name',
        'id'
    ]

    expected_timestamps = pd.to_datetime(pd.Series([_TIME_1, _TIME_2, _TIME_3]), utc=True).to_list()
    actual_timestamps = df['timestamp'].to_list()

    assert sorted(expected_columns) == sorted(df.columns.to_list())

    assert sorted(expected_timestamps) == sorted(actual_timestamps)


@pytest.mark.filterwarnings('ignore:No file content available for files')
@pytest.mark.filterwarnings('ignore:Multiple inspection logs found referring to the same file.')
def test_as_binary_classification_input(mock_url, mock_fetch):
    inspection_logs = InspectionLogSet([])
    inspection_logs.elements = [InspectionLog(response) for response in deepcopy(_MOCK_RESPONSE)]

    details_list = [deepcopy(_DETAILS_1), deepcopy(_DETAILS_2), deepcopy(_DETAILS_3)]
    mock_fetch.side_effect = details_list

    df, images = inspection_logs.as_binary_classification_input()

    assert len(df) == 2
    assert len(images) == 2

    expected_columns = [
        'file_id', 'timestamp', 'type', 'is_conformant',
        'sfc', 'material', 'operation', 'plant', 'resource', 'routing', 'source', 'view_name',
        'id'
    ]

    expected_timestamps = pd.to_datetime(pd.Series([_TIME_1, _TIME_3]), utc=True).to_list()
    unexpected_timestamps = pd.to_datetime(pd.Series([_TIME_2]), utc=True).to_list()
    actual_timestamps = df['timestamp'].to_list()

    assert sorted(expected_columns) == sorted(df.columns.to_list())

    assert sorted(expected_timestamps) == sorted(actual_timestamps)

    for ts in unexpected_timestamps:
        assert ts not in actual_timestamps

    for _, row in df.iterrows():
        assert row['is_conformant'] in [True, False]


@pytest.mark.filterwarnings('ignore:No file content available for files')
@pytest.mark.filterwarnings('ignore:Multiple inspection logs found referring to the same file.')
def test_as_multilabel_classification_input(mock_url, mock_fetch):
    inspection_logs = InspectionLogSet([])
    inspection_logs.elements = [InspectionLog(response) for response in deepcopy(_MOCK_RESPONSE)]

    details_list = [deepcopy(_DETAILS_1), deepcopy(_DETAILS_2), deepcopy(_DETAILS_3)]
    mock_fetch.side_effect = details_list

    df, images = inspection_logs.as_multilabel_classification_input()

    assert len(df) == 2
    assert len(images) == 2

    expected_columns = [
        'file_id', 'timestamp', 'type', 'logged_nc_code', 'predicted_nc_code', 'is_conformant', 'logged_nc_details',
        'predicted_nc_details', 'sfc', 'material', 'operation', 'plant', 'resource', 'routing', 'source', 'view_name',
        'id'
    ]

    expected_timestamps = pd.to_datetime(pd.Series([_TIME_1, _TIME_2]), utc=True).to_list()
    unexpected_timestamps = pd.to_datetime(pd.Series([_TIME_3]), utc=True).to_list()
    actual_timestamps = df['timestamp'].to_list()

    assert sorted(expected_columns) == sorted(df.columns.to_list())

    assert sorted(expected_timestamps) == sorted(actual_timestamps)

    for ts in unexpected_timestamps:
        assert ts not in actual_timestamps

    for _, row in df.iterrows():
        assert (row['predicted_nc_details'] != '[]') or (row['loggend_nc_details'] != '[]')


def _contains_bounding_box(row):
    for prediction in row['predicted_nc_details']:
        if 'predictionBoundingBoxCoords' in prediction.keys():
            if prediction['predictionBoundingBoxCoords'] != '[]':
                return True

    for logged_ncs in row['logged_nc_details']:
        if 'defectBoundingBoxCoords' in logged_ncs.keys():
            if logged_ncs['defectBoundingBoxCoords'] != '[]':
                return True

    return False


@pytest.mark.filterwarnings('ignore:No file content available for files')
@pytest.mark.filterwarnings('ignore:Multiple inspection logs found referring to the same file.')
def test_as_object_detection_input(mock_url, mock_fetch):
    inspection_logs = InspectionLogSet([])
    inspection_logs.elements = [InspectionLog(response) for response in deepcopy(_MOCK_RESPONSE)]

    details_list = [deepcopy(_DETAILS_1), deepcopy(_DETAILS_2), deepcopy(_DETAILS_3)]
    mock_fetch.side_effect = details_list

    df, images = inspection_logs.as_object_detection_input()

    assert len(df) == 1
    assert len(images) == 1

    expected_columns = [
        'file_id', 'timestamp', 'type', 'logged_nc_code', 'predicted_nc_code', 'is_conformant', 'logged_nc_details',
        'predicted_nc_details', 'sfc', 'material', 'operation', 'plant', 'resource', 'routing', 'source', 'view_name',
        'id'
    ]

    expected_timestamps = pd.to_datetime(pd.Series([_TIME_1]), utc=True).to_list()
    unexpected_timestamps = pd.to_datetime(pd.Series([_TIME_2, _TIME_3]), utc=True).to_list()
    actual_timestamps = df['timestamp'].to_list()

    assert sorted(expected_columns) == sorted(df.columns.to_list())

    assert sorted(expected_timestamps) == sorted(actual_timestamps)

    for ts in unexpected_timestamps:
        assert ts not in actual_timestamps

    expected_images = {
        _FILE_1: b64decode(_FILE_1_CONTENT),
    }

    assert images == expected_images

    for _, row in df.iterrows():
        assert (row['predicted_nc_details'] != '[]') or (row['logged_nc_details'] != '[]')
        assert _contains_bounding_box(row)
