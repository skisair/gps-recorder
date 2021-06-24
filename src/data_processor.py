import os
import logging
import json
from datetime import timezone, timedelta
import glob

import paho.mqtt.client as mqtt

from util.exporter import LocalExporter, AzureExporter

LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


class GpsEventHandler:

    def __init__(self):
        self.exporters = []

    def add(self, exporter):
        self.exporters.append(exporter)

    def on_connect(self, client, userdata, flags, respons_code):
        logger.info(f'connected to mqtt server:{respons_code}')
        client.subscribe(client.topic)

    def on_message(self, client, userdata, message):
        topic = message.topic
        data = message.payload.decode()
        logger.debug(f'{topic} : {data}')
        json_message = json.loads(data)
        self.export(json_message)

    def export(self, message:dict ):
        for exporter in self.exporters:
            exporter.export(message)


class DataProcessor:
    def __init__(self, mqtt_host, mqtt_port, topic, event_handler):
        self.running = True
        self.event_handler = event_handler
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.mqtt_client.topic = topic
        self.mqtt_client.on_connect = self.event_handler.on_connect
        self.mqtt_client.on_message = self.event_handler.on_message

    def run(self):
        self.mqtt_client.connect(mqtt_host, port=mqtt_port, keepalive=keep_alive)
        self.mqtt_client.loop_forever()

    def stop(self):
        self.running = False
        self.mqtt_client.disconnect()


if __name__ == '__main__':
    device_id = os.environ.get('DATA_PROCESSOR_ID', default='data_processor')

    exporters = os.environ.get('DEVICE_EXPORTER', default='LOCAL,AZURE').split(',')

    mqtt_host = os.environ.get('MQTT_HOST', default='localhost')
    mqtt_port = int(os.environ.get('MQTT_PORT', default=1883))
    keep_alive = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))
    # センサーから上がってくる情報は全部。
    subscribe_mqtt_topic = os.environ.get('MQTT_TOPIC', default='sensor/#')

    batch_input = os.environ.get('BATCH_INPUT_FOLDER', default='')

    event_handler = GpsEventHandler()

    if 'LOCAL' in exporters:
        local_exporter = LocalExporter(device_id)
        event_handler.add(local_exporter)

    if 'AZURE' in exporters:
        azure_exporter = AzureExporter()
        event_handler.add(azure_exporter)

    if len(batch_input) > 0:
        files = glob.glob( os.path.join(batch_input,'/**/*.json'), recursive=True)
        for file in files:
            with open(file, mode='r') as f:
                message = json.load(f)
                event_handler.export(message)
    else:

        data_processor = DataProcessor(mqtt_host=mqtt_host,
                                       mqtt_port=mqtt_port,
                                       topic=subscribe_mqtt_topic,
                                       event_handler=event_handler)
        data_processor.run()
