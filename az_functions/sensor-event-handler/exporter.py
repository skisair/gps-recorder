import os
import logging
from datetime import datetime, timezone, timedelta
from azure.cosmosdb.table.tableservice import TableService

LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)

CONNECTION_STRING = \
    'DefaultEndpointsProtocol=http;' \
    'AccountName=devstoreaccount1;' \
    'AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;' \
    'BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;' \
    'QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;' \
    'TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;'


class AzureExporter:

    def __init__(self):
        self.connect_string = os.environ.get('AZURE_STORAGE_CONNECT_STRING',
                                             default=CONNECTION_STRING)
        self.table_service = TableService(connection_string=self.connect_string)
        self.mdevice_table_name = 'mdevice'
        self.mdatatable_name = 'mdata'
        self.tdata_table_name = 'tdata'
        __ = self.table_service.create_table(self.mdevice_table_name)
        __ = self.table_service.create_table(self.mdatatable_name)
        __ = self.table_service.create_table(self.tdata_table_name)

        self.mdevice_table = []
        self.mdata_table = []

    def export(self, message):
        """
        Azureへデータ出力
        :param message:
        :return:
        """
        '''
        - デバイスマスタ mdevice
          - PK: デバイスID device_id
          - RK: データ種別ID data_id
          - デバイス名 device_name
        
        - データ種別マスタ mdata
          - PK: データ種別ID data_id
          - RK: 項目ID item_id 
          - 項目名 item_name
          - Max値 value_max
          - Min値 value_min
          
        - データトラン tdata
          - PK: デバイスID-データ種別
          - RK: タイムスタンプ
        '''
        device_id = message['device_id']
        data_id = message['data_id']

        if (device_id + '_' + data_id) not in self.mdevice_table:
            mdevice = {
                'PartitionKey': device_id,
                'RowKey': data_id,
                'device_id': device_id,
                'data_id': data_id,
            }
            self.table_service.insert_or_merge_entity(self.mdevice_table_name , mdevice)

            self.mdevice_table.append((device_id + '_' + data_id))

        for item_id in message:
            if (data_id + '_' + item_id) not in self.mdata_table:
                mdata = {
                    'PartitionKey': data_id,
                    'RowKey': item_id,
                    'data_id': data_id,
                    'item_id': item_id,
                }
                self.table_service.insert_or_merge_entity(self.mdatatable_name , mdata)
                self.mdata_table.append((data_id + '_' + item_id) )

        partition_key = device_id + '_' + data_id
        row_key = message['local_time']
        message['PartitionKey'] = partition_key
        message['RowKey'] = row_key
        self.table_service.insert_or_replace_entity(self.tdata_table_name , message)
