from collections import defaultdict
from io import BytesIO
from unittest.mock import patch, call

import pytest
import pandas as pd

from sailor.sap_iot.fetch import _start_bulk_timeseries_data_export, _check_bulk_timeseries_export_status,\
    _get_exported_bulk_timeseries_data, _process_one_file, get_indicator_data
from sailor.sap_iot import TimeseriesDataset
from sailor.assetcentral.indicators import IndicatorSet
from sailor.assetcentral.equipment import EquipmentSet
from sailor.utils.oauth_wrapper import RequestError
from sailor.utils.utils import DataNotFoundWarning


@pytest.fixture()
def make_csv_bytes():
    def maker(group_id=1, model_id='model_id'):
        data = '''
        "_TIME","I_indicator_id_1","I_indicator_id_2","indicatorGroupId","modelId","templateId","equipmentId"
        "1601683140000","3.4","1.78","IG_indicator_group_id_{gid}","{mid}","template_id_1","equipment_id_1"
        "1601683140000","4.5","2.4","IG_indicator_group_id_{gid}","{mid}","template_id_1","equipment_id_2"
        "1601683180000","4.3","78.1","IG_indicator_group_id_{gid}","{mid}","template_id_1","equipment_id_1"
        "1601683180000","5.4","4.2","IG_indicator_group_id_{gid}","{mid}","template_id_1","equipment_id_2"
        "1601683140000","13.4","11.78","IG_indicator_group_id_{gid}","{mid}","template_id_2","equipment_id_1"
        "1601683140000","14.5","12.4","IG_indicator_group_id_{gid}","{mid}","template_id_2","equipment_id_2"
        "1601683180000","14.3","178.1","IG_indicator_group_id_{gid}","{mid}","template_id_2","equipment_id_1"
        "1601683180000","15.4","14.2","IG_indicator_group_id_{gid}","{mid}","template_id_2","equipment_id_2"
        '''.format(gid=group_id, mid=model_id)

        return ''.join(data.split(' ')).encode()
    return maker


@pytest.fixture
def mock_fetch(mock_config):
    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request') as mock:
        yield mock


class TestRawDataAsyncFunctions:
    def test_export_start_request_delegate_call(self, mock_fetch, mock_config):
        mock_config.config.sap_iot = defaultdict(str, export_url='EXPORT_BASE_URL')
        expected_url = 'EXPORT_BASE_URL/v1/InitiateDataExport/indicator_group_id?timerange=start_date-end_date'

        _start_bulk_timeseries_data_export('start_date', 'end_date', 'indicator_group_id')

        mock_fetch.assert_called_once_with('POST', expected_url)

    def test_export_status_request_delegate_call(self, mock_fetch, mock_config):
        mock_config.config.sap_iot = defaultdict(str, export_url='EXPORT_BASE_URL')
        mock_fetch.return_value = dict(Status='The file is available for download.')
        expected_url = 'EXPORT_BASE_URL/v1/DataExportStatus?requestId=export_id'

        _check_bulk_timeseries_export_status('export_id')

        mock_fetch.assert_called_once_with('GET', expected_url)

    @patch('sailor.sap_iot.fetch.zipfile.ZipFile')
    def test_export_get_data_request_delegate_call(self, mock_zipfile, mock_fetch, mock_config):
        mock_config.config.sap_iot = defaultdict(str, download_url='DOWNLOAD_BASE_URL')
        expected_url = "DOWNLOAD_BASE_URL/v1/DownloadData('export_id')"
        mock_fetch.return_value = b''

        with pytest.raises(RuntimeError):
            _get_exported_bulk_timeseries_data('export_id', IndicatorSet([]), EquipmentSet([]))

        mock_fetch.assert_called_once_with('GET', expected_url, headers={'Accept': 'application/octet-stream'})

    def test_export_get_data_request_invalid_zipfile_response(self, mock_fetch):
        mock_fetch.return_value = b''

        with pytest.raises(RuntimeError) as exception_info:
            _get_exported_bulk_timeseries_data('export_id', IndicatorSet([]), EquipmentSet([]))

        assert str(exception_info.value) == 'Downloaded file is corrupted, can not process contents.'

    def test_export_get_data_request_empty_zipfile_response(self, mock_fetch):
        mock_fetch.return_value = bytes.fromhex('504B050600000000000000000000000000000000000000000000')  # minimal zip

        with pytest.raises(RuntimeError) as exception_info:
            _get_exported_bulk_timeseries_data('export_id', IndicatorSet([]), EquipmentSet([]))

        assert str(exception_info.value) == 'Downloaded File did not have any content.'

    @patch('sailor.sap_iot.fetch.zipfile')
    def test_export_get_data_request_empty_gzip_content(self, mock_zipfile, mock_fetch):
        mock_fetch.return_value = b''
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1', 'inner_file_2']
        mock_zipfile.ZipFile.return_value.read.return_value = b''

        with pytest.raises(RuntimeError) as exception_info:
            _get_exported_bulk_timeseries_data('export_id', IndicatorSet([]), EquipmentSet([]))

        assert str(exception_info.value) == 'Downloaded File did not have any content.'

    @patch('sailor.sap_iot.fetch.zipfile')
    def test_export_get_data_request_invalid_gzip_content(self, mock_zipfile, mock_fetch):
        mock_fetch.return_value = b''
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1', 'inner_file_2']
        mock_zipfile.ZipFile.return_value.read.return_value = b'INVALID'

        with pytest.raises(RuntimeError) as exception_info:
            _get_exported_bulk_timeseries_data('export_id', IndicatorSet([]), EquipmentSet([]))

        assert str(exception_info.value) == 'Downloaded file is corrupted, can not process contents.'

    @pytest.mark.parametrize('description,response,expected', [
        ('available status', 'The file is available for download.', True),
        ('unavailable status', 'Request for data download is submitted.', False),
    ])
    def test_export_status_request_good_response(self, mock_fetch, response, expected, description):
        mock_fetch.return_value = dict(Status=response)

        assert _check_bulk_timeseries_export_status('export_id') == expected

    @pytest.mark.parametrize('description,response', [
        ('empty status', ''),
        ('None status', None),
        ('Failed status', 'File download has failed. Re-initiate the request for data export.')
    ])
    def test_export_status_request_bad_response(self, mock_fetch, response, description):
        mock_fetch.return_value = dict(Status=response)

        with pytest.raises(RuntimeError) as exception_info:
            _check_bulk_timeseries_export_status('export_id')

        assert str(exception_info.value) == str(response)

    @pytest.mark.parametrize('description,indicator_ids,template_ids,equipment_ids,expected_rows', [
        ('filter_indicator', [1, 1], [1, 2], [1, 2], 4),
        ('filter_template', [1, 2], [1, 2], [1, 2], 4),
        ('filter_equipment', [1, 2, 1, 2], [1, 1, 2, 2], [1], 2),
        ('no filters', [1, 2, 1, 2], [1, 1, 2, 2], [1, 2], 4)
    ])
    def test_process_one_file_filtering(self, make_csv_bytes, make_indicator_set, make_equipment_set,
                                        indicator_ids, template_ids, equipment_ids, expected_rows, description):
        indicator_set = make_indicator_set(propertyId=[f'indicator_id_{x}' for x in indicator_ids],
                                           categoryID=[f'template_id_{x}' for x in template_ids],
                                           pstid=['indicator_group_id_1'] * len(indicator_ids))
        equipment_set = make_equipment_set(equipmentId=[f'equipment_id_{x}' for x in equipment_ids])
        expected_columns = ['timestamp', 'equipment_id']
        expected_columns += [indicator._unique_id for indicator in indicator_set]
        expected_equipments = {equipment.id for equipment in equipment_set}

        data = _process_one_file(BytesIO(make_csv_bytes()), indicator_set, equipment_set)

        assert isinstance(data, pd.DataFrame)
        assert list(data.columns) == expected_columns
        assert len(data) == expected_rows
        assert set(data['equipment_id'].unique()) == expected_equipments


class TestRawDataWrapperFunction:
    @patch('sailor.sap_iot.fetch.gzip.GzipFile')
    @patch('sailor.sap_iot.fetch.zipfile')
    def test_get_indicator_data_two_indicator_groups(self, mock_zipfile, mock_gzip, mock_config, mock_fetch,
                                                     make_indicator_set, make_equipment_set, make_csv_bytes):
        mock_config.config.sap_iot = defaultdict(str, export_url='EXPORT_URL', download_url='DOWNLOAD_URL')

        indicator_set = make_indicator_set(propertyId=[f'indicator_id_{x}' for x in [1, 2, 1, 2]],
                                           categoryID=[f'template_id_{x}' for x in [1, 1, 2, 2]],
                                           pstid=[f'indicator_group_id_{x}' for x in [1, 1, 2, 2]])
        equipment_set = make_equipment_set(equipmentId=[f'equipment_id_{x}' for x in [1, 2]])

        mock_fetch.side_effect = [
            {'RequestId': 'test_request_id_1'}, {'RequestId': 'test_request_id_2'},
            {'Status': 'The file is available for download.'}, b'mock_zip_content',
            {'Status': 'The file is available for download.'}, b'mock_zip_content',
        ]
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1']
        mock_zipfile.ZipFile.return_value.read.return_value = b'mock_gzip_content'
        mock_gzip.side_effect = [BytesIO(make_csv_bytes(1)), BytesIO(make_csv_bytes(2))]

        expected_calls = [
            call('POST', 'EXPORT_URL/v1/InitiateDataExport/IG_indicator_group_id_1?timerange=2020-10-01-2020-11-01'),
            call('POST', 'EXPORT_URL/v1/InitiateDataExport/IG_indicator_group_id_2?timerange=2020-10-01-2020-11-01'),
            call('GET', 'EXPORT_URL/v1/DataExportStatus?requestId=test_request_id_1'),
            call('GET', "DOWNLOAD_URL/v1/DownloadData('test_request_id_1')", headers={
                                                                            'Accept': 'application/octet-stream'}),
            call('GET', 'EXPORT_URL/v1/DataExportStatus?requestId=test_request_id_2'),
            call('GET', "DOWNLOAD_URL/v1/DownloadData('test_request_id_2')", headers={
                                                                            'Accept': 'application/octet-stream'}),
        ]

        expected_columns = ['timestamp', 'equipment_id']
        expected_columns += [indicator._unique_id for indicator in indicator_set]

        wrapper = get_indicator_data('2020-10-01T00:00:00Z', '2020-11-01T00:00:00Z', indicator_set, equipment_set)

        mock_fetch.assert_has_calls(expected_calls)
        assert isinstance(wrapper, TimeseriesDataset)
        assert set(wrapper._df.columns) == set(expected_columns)
        assert len(wrapper._df) == 4
        assert set(wrapper._df['equipment_id'].unique()) == {'equipment_id_1', 'equipment_id_2'}

    @patch('sailor.sap_iot.fetch.gzip.GzipFile')
    @patch('sailor.sap_iot.fetch.zipfile')
    @pytest.mark.parametrize('description,equipment_id', [
        ('equipment_id matches', 'equipment_id_1'),
        ('equipment_id does not match', 'equipment_id_4'),
    ])
    @pytest.mark.filterwarnings('ignore:Could not find any data for indicator')
    @pytest.mark.filterwarnings('ignore:There is no data in the dataframe for some of the indicators')
    @pytest.mark.filterwarnings('ignore:There is no data in the dataframe for some of the equipments')
    def test_get_indicator_data_empty_csv_column_merge(self, mock_zipfile, mock_gzip, mock_config, mock_fetch,
                                                       make_indicator_set, make_equipment_set, make_csv_bytes,
                                                       description, equipment_id):
        # When columns in the csv returned are empty (as 'modelId' is in this test) the data type of those
        # columns is set to float64 by the pandas csv parser.
        # If in addition the resulting Dataframe is filtered empty (eg because no equipment match the equipment
        # selector passed to get_indicator_data) the pd.merge call in get_indicator_data fails with
        # ` ValueError: You are trying to merge on object and float64 columns.`.
        # It's not clear why this error does not occur when the csv file is not filtered to be empty, even though
        # the dtypes are still float64.
        # This test will ascertain that the pd.merge in get_indicator_data works successfully when the csv `modelId`
        # column is empty for both cases -- resulting DataFrame filtered empty, and resulting DataFrame with content.

        mock_config.config.sap_iot = defaultdict(str, export_url='EXPORT_URL', download_url='DOWNLOAD_URL')

        indicator_set = make_indicator_set(propertyId=['indicator_id_1'])
        equipment_set = make_equipment_set(equipmentId=[equipment_id])

        mock_fetch.side_effect = [
            {'RequestId': 'test_request_id_1'},
            {'Status': 'The file is available for download.'}, b'mock_zip_content',
        ]
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1']
        mock_zipfile.ZipFile.return_value.read.return_value = b'mock_gzip_content'
        mock_gzip.side_effect = [BytesIO(make_csv_bytes(1, ''))]

        get_indicator_data('2020-01-01T00:00:00Z', '2020-02-01T00:00:00Z', indicator_set, equipment_set)

    def test_get_indicator_data_requesterror_handled(self, mock_fetch, make_indicator_set):
        mock_fetch.side_effect = RequestError('msg', '400', 'reason',
                                              '{"message": "Data not found for the requested date range"}')
        indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'])

        with pytest.warns(DataNotFoundWarning, match='No data for indicator group IG_group_id.*'):
            get_indicator_data('2020-01-01T00:00:00Z', '2020-02-01T00:00:00Z', indicator_set, EquipmentSet([]))

    @pytest.mark.parametrize('description,content', [
        ('not json', 'foo'),
        ('empty', ''),
        ('wrong content', '{"message": "Test Content"}'),
        ('no field', '{"some_other_field": "Test Content"}')
    ])
    def test_get_indicator_data_requesterror_unhandled(self, mock_fetch, make_indicator_set,
                                                       content, description):
        mock_fetch.side_effect = RequestError(content, '400', 'reason', content)
        indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'])

        with pytest.raises(RequestError) as exception_info:
            get_indicator_data('2020-01-01T00:00:00Z', '2020-02-01T00:00:00Z', indicator_set, EquipmentSet([]))

        assert str(exception_info.value) == content

    @patch('sailor.sap_iot.fetch.gzip.GzipFile')
    @patch('sailor.sap_iot.fetch.zipfile')
    def test_get_indicator_data_missing_indicator_warning(self, mock_zipfile, mock_gzip, mock_config, mock_fetch,
                                                          make_indicator_set, make_equipment_set, make_csv_bytes):

        mock_config.config.sap_iot = defaultdict(str, export_url='EXPORT_URL', download_url='DOWNLOAD_URL')

        indicator_set = make_indicator_set(propertyId=[f'indicator_id_{x}' for x in [1, 2, 3]],
                                           categoryID=[f'template_id_{x}' for x in [1, 1, 1]],
                                           pstid=['indicator_group_id_1'] * 3)
        equipment_set = make_equipment_set(equipmentId=[f'equipment_id_{x}' for x in [1, 2]])

        mock_fetch.side_effect = [
            {'RequestId': 'test_request_id_1'},
            {'Status': 'The file is available for download.'}, b'mock_zip_content',
        ]
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1']
        mock_zipfile.ZipFile.return_value.read.return_value = b'mock_gzip_content'
        mock_gzip.side_effect = [BytesIO(make_csv_bytes())]

        with pytest.warns(DataNotFoundWarning, match='Could not find any data for indicator.*indicator_id_3.*'):
            get_indicator_data('2020-01-01T00:00:00Z', '2020-02-01T00:00:00Z', indicator_set, equipment_set)


class TestPrintProgressUpdates:
    @patch('sailor.sap_iot.fetch.gzip.GzipFile')
    @patch('sailor.sap_iot.fetch.zipfile')
    def test_print_one_group_no_export(self, mock_zipfile, mock_gzip, mock_config, mock_fetch,
                                       make_indicator_set, make_equipment_set, make_csv_bytes,
                                       capfd):
        indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'],
                                           pstid=['group_id_1', 'group_id_1'],
                                           indicatorGroupName=['group1', 'group1'])
        equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'])

        mock_fetch.side_effect = [
            {'RequestId': 'test_request_id_1'},
            {'Status': 'The file is available for download.'},
            b'mock_zip_content',
        ]
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1']
        mock_zipfile.ZipFile.return_value.read.return_value = b'mock_gzip_content'
        mock_gzip.side_effect = [BytesIO(make_csv_bytes())]

        get_indicator_data('2020-10-01T00:00:00Z', '2020-11-01T00:00:00Z', indicator_set, equipment_set)
        captured_output, _ = capfd.readouterr()

        assert captured_output == (
            'Data export triggered for 1 indicator group(s).\n'
            'Waiting for data export:\n'
            '\n'
            'Now downloading export for indicator group group1.\n'
            'processing compressed file 1/1\x1b[2K\r\n'
            'Download complete\n'
            '\n'
        )

    @patch('sailor.sap_iot.fetch.gzip.GzipFile')
    @patch('sailor.sap_iot.fetch.zipfile')
    def test_print_two_groups_no_export(self, mock_zipfile, mock_gzip, mock_config, mock_fetch,
                                        make_indicator_set, make_equipment_set, make_csv_bytes,
                                        capfd):
        indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'],
                                           pstid=['group_id_1', 'group_id_2'],
                                           indicatorGroupName=['group1', 'group2'])
        equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'])

        mock_fetch.side_effect = [
            {'RequestId': 'test_request_id_1'},
            {'RequestId': 'test_request_id_2'},
            {'Status': 'The file is available for download.'},
            b'mock_zip_content',
            {'Status': 'The file is available for download.'},
            b'mock_zip_content',
        ]
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1']
        mock_zipfile.ZipFile.return_value.read.return_value = b'mock_gzip_content'
        mock_gzip.side_effect = [BytesIO(make_csv_bytes(1)), BytesIO(make_csv_bytes(2))]

        get_indicator_data('2020-10-01T00:00:00Z', '2020-11-01T00:00:00Z', indicator_set, equipment_set)
        captured_output, _ = capfd.readouterr()

        assert captured_output == (
            'Data export triggered for 2 indicator group(s).\n'
            'Waiting for data export:\n'
            '\n'
            'Now downloading export for indicator group group1.\n'
            'processing compressed file 1/1\x1b[2K\r\n'
            'Download complete\n'
            '\n'
            'Now downloading export for indicator group group2.\n'
            'processing compressed file 1/1\x1b[2K\r\n'
            'Download complete\n'
            '\n'
        )

    @patch('sailor.sap_iot.fetch.time')
    @patch('sailor.sap_iot.fetch.gzip.GzipFile')
    @patch('sailor.sap_iot.fetch.zipfile')
    def test_print_one_group_with_export(self, mock_zipfile, mock_gzip, mock_time, mock_config, mock_fetch,
                                         make_indicator_set, make_equipment_set, make_csv_bytes,
                                         capfd):
        indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'],
                                           pstid=['group_id_1', 'group_id_1'],
                                           indicatorGroupName=['group1', 'group1'])
        equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'])

        mock_fetch.side_effect = [
            {'RequestId': 'test_request_id_1'},
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'The file is available for download.'},
            b'mock_zip_content',
        ]
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1']
        mock_zipfile.ZipFile.return_value.read.return_value = b'mock_gzip_content'
        mock_gzip.side_effect = [BytesIO(make_csv_bytes(1))]

        get_indicator_data('2020-10-01T00:00:00Z', '2020-11-01T00:00:00Z', indicator_set, equipment_set)
        captured_output, _ = capfd.readouterr()

        assert captured_output == (
            'Data export triggered for 1 indicator group(s).\n'
            'Waiting for data export:\n'
            '..\n'
            'Now downloading export for indicator group group1.\n'
            'processing compressed file 1/1\x1b[2K\r\n'
            'Download complete\n'
            '\n'
        )

    @patch('sailor.sap_iot.fetch.time')
    @patch('sailor.sap_iot.fetch.gzip.GzipFile')
    @patch('sailor.sap_iot.fetch.zipfile')
    def test_print_two_groups_with_export(self, mock_zipfile, mock_gzip, mock_time, mock_config, mock_fetch,
                                          make_indicator_set, make_equipment_set, make_csv_bytes,
                                          capfd):
        indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'],
                                           pstid=['group_id_1', 'group_id_2'],
                                           indicatorGroupName=['group1', 'group2'])
        equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'])

        mock_fetch.side_effect = [
            {'RequestId': 'test_request_id_1'},
            {'RequestId': 'test_request_id_2'},
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'The file is available for download.'},
            b'mock_zip_content',
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'Request for data download is initiated.'},
            {'Status': 'The file is available for download.'},
            b'mock_zip_content',
        ]
        mock_zipfile.ZipFile.return_value.filelist = ['inner_file_1']
        mock_zipfile.ZipFile.return_value.read.return_value = b'mock_gzip_content'
        mock_gzip.side_effect = [BytesIO(make_csv_bytes(1)), BytesIO(make_csv_bytes(2))]

        get_indicator_data('2020-10-01T00:00:00Z', '2020-11-01T00:00:00Z', indicator_set, equipment_set)
        captured_output, _ = capfd.readouterr()

        assert captured_output == (
            'Data export triggered for 2 indicator group(s).\n'
            'Waiting for data export:\n'
            '..\n'
            'Now downloading export for indicator group group1.\n'
            'processing compressed file 1/1\x1b[2K\r\n'
            'Download complete\n'
            '..\n'
            'Now downloading export for indicator group group2.\n'
            'processing compressed file 1/1\x1b[2K\r\n'
            'Download complete\n'
            '\n'
        )
