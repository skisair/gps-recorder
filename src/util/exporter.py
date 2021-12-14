import os
import json
import logging
import queue
from datetime import datetime, timezone, timedelta
import uuid
from string import Template
import ssl

import paho.mqtt.client as mqtt
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


'''
path_to_root_cert = "<local path to digicert.cer file>"
device_id = "<device id from device registry>"
sas_token = "<generated SAS token>"
iot_hub_name = "<iot hub name>"
user_name = iot_hub_name+".azure-devices.net/" + device_id + "/?api-version=2018-06-30"
host_name = iot_hub_name+".azure-devices.net"
'''


class MqttExporter:
    def __init__(self, device_id: str):
        # IOT HUB でのTOPIC　devices/{device_id}/messages/events/{property_bag}
        self.device_id = device_id
        self.mqtt_host = os.environ.get('MQTT_HOST', default='localhost')
        self.mqtt_port = int(os.environ.get('MQTT_PORT', default=1883))
        self.keep_alive = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))
        self.mqtt_topic = os.environ.get('MQTT_TOPIC', default='devices/${device_id}/messages/events/?data_id=${data_id}')

        # 認証処理関連
        self.path_to_root_cert = os.environ.get('MQTT_ROOT_CERT_PATH', default=None)
        self.path_to_cert_file = os.environ.get('MQTT_CERT_PATH', default=None)
        self.path_to_key_file = os.environ.get('MQTT_KEY_PATH', default=None)
        self.ssl_cert = os.environ.get('SSL_CERT',default='CERT_NONE')
        if self.ssl_cert == 'CERT_NONE':
            self.ssl_cert = ssl.CERT_NONE
        elif self.ssl_cert == 'CERT_REQUIRED':
            self.ssl_cert = ssl.CERT_REQUIRED
        else:
            self.ssl_cert = ssl.CERT_NONE

        self.mqtt_user_name = os.environ.get('MQTT_USER_NAME', default=None)
        self.mqtt_password = os.environ.get('MQTT_PASSWORD', default=None)

        self.mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.mqtt_client.username_pw_set(
            username=self.mqtt_user_name,
            password=self.mqtt_password,
        )
        self.mqtt_client.tls_set(
            ca_certs=self.path_to_root_cert,
            certfile=self.path_to_cert_file,
            keyfile=self.path_to_key_file,
            #cert_reqs=ssl.CERT_REQUIRED,
            cert_reqs=self.ssl_cert,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None)
        self.mqtt_client.tls_insecure_set(True)
        self.mqtt_client.connect(self.mqtt_host, port=self.mqtt_port, keepalive=self.keep_alive)
        #　self.client.connect(self.mqtt_host, port=self.mqtt_port , keepalive=self.keep_alive)

    def export(self, message):
        data_id = message['data_id']
        topic = Template(self.mqtt_topic).substitute(device_id=self.device_id, data_id=data_id, **os.environ)
        output_string = json.dumps(message)
        logger.debug(f'{topic}:{output_string}')
        self.mqtt_client.publish(topic, output_string)


class LocalExporter:
    """
    ローカル出力クラス
    """
    def __init__(self, device_id: str):
        """
        環境変数
        OUTPUT_FOLDER : 出力先フォルダパス data/${device_id}
        OUTPUT_FOLDER_FORMAT : 出力先振分フォーマット %Y/%m/%d/%H
        OUTPUT_FILE_FORMAT : 出力ファイル名 %Y%m%d%H%M%S%f-${id}.json
        (idはuuidにより一意な値を入れ、重複を防ぐ）
        :param device_id: デバイスID
        """
        self.device_id = device_id
        # 出力フォルダの設定作成
        self.output_folder = os.environ.get('OUTPUT_FOLDER', default='data/${device_id}')
        self.output_folder = Template(self.output_folder).substitute(device_id=device_id, **os.environ)
        self.output_folder_format = os.environ.get('OUTPUT_FOLDER_FORMAT', default='%Y/%m/%d/%H')
        self.output_file_format = os.environ.get('OUTPUT_FILE_FORMAT', default='%Y%m%d%H%M%S%f-${data_id}-${id}.json')
        os.makedirs(self.output_folder, exist_ok=True)

    def export(self, message):
        """
        メッセージの出力（フォルダにJSONで保存）
        :param message:
        :return:
        """
        unique_id = str(uuid.uuid4())
        output_string = json.dumps(message)
        if 'data_id' in message:
            data_id = message['data_id']
        else:
            data_id = '____'
        file_name = datetime.now(JST).strftime(
            Template(self.output_file_format).substitute(id=unique_id, device_id=self.device_id, data_id=data_id, **os.environ))
        folder = datetime.now(JST).strftime(
            Template(self.output_folder_format).substitute(id=unique_id, device_id=self.device_id, data_id=data_id, **os.environ))
        folder = os.path.join(self.output_folder, folder)
        os.makedirs(folder, exist_ok=True)
        with open(file=os.path.join(folder, file_name), mode='w', encoding='UTF-8') as f:
            f.write(output_string)

queue_list = {}

class QueueExporter:
    """
    ローカル出力クラス
    """
    def __init__(self, device_id: str, mem_queue):
        """
        環境変数
        OUTPUT_FOLDER : 出力先フォルダパス data/${device_id}
        OUTPUT_FOLDER_FORMAT : 出力先振分フォーマット %Y/%m/%d/%H
        OUTPUT_FILE_FORMAT : 出力ファイル名 %Y%m%d%H%M%S%f-${id}.json
        (idはuuidにより一意な値を入れ、重複を防ぐ）
        :param device_id: デバイスID
        """
        self.mem_queue = mem_queue
        self.device_id = device_id
        # 出力フォルダの設定作成
        self.output_folder = os.environ.get('OUTPUT_FOLDER', default='data/${device_id}')
        self.output_folder = Template(self.output_folder).substitute(device_id=device_id, **os.environ)
        self.output_folder_format = os.environ.get('OUTPUT_FOLDER_FORMAT', default='%Y/%m/%d/%H')
        self.output_file_format = os.environ.get('OUTPUT_FILE_FORMAT', default='%Y%m%d%H%M%S%f-${data_id}-${id}.json')
        os.makedirs(self.output_folder, exist_ok=True)

    def export(self, message):
        """
        メッセージの出力（フォルダにJSONで保存）
        :param message:
        :return:
        """
        self.mem_queue.put(message)
