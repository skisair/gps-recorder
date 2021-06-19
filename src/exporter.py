import os
import json
import logging
from datetime import datetime, timezone, timedelta
import uuid
from string import Template

import paho.mqtt.client as mqtt

LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


class MqttExporter:

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.mqtt_host = os.environ.get('MQTT_HOST', default='localhost')
        self.mqtt_port = int(os.environ.get('MQTT_PORT', default=1883))
        self.keep_alive = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))
        self.mqtt_topic = os.environ.get('MQTT_TOPIC', default='gps/sensor_data')

        self.client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.client.connect(self.mqtt_host, port=self.mqtt_port , keepalive=self.keep_alive)

    def export(self, message):
        output_string = json.dumps(message)
        self.client.publish(self.mqtt_topic, output_string)


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
