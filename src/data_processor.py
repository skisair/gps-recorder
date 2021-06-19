import os
import logging
import json
from datetime import datetime, timezone, timedelta

import paho.mqtt.client as mqtt

from exporter import LocalExporter

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
        data = message.payload.decode()
        logger.debug(f'{message.topic} {data}')
        org_message = json.loads(data)
        for exporter in self.exporters:
            exporter.export(org_message)


if __name__ == '__main__':

    device_id = os.environ.get('DATA_PROCESSOR_ID', default='data_processor')
    mqtt_host = os.environ.get('MQTT_HOST', default='localhost')
    mqtt_port = int(os.environ.get('MQTT_PORT', default=1883))
    keep_alive = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))
    mqtt_topic = os.environ.get('MQTT_TOPIC', default='gps/sensor_data')

    event_handler = GpsEventHandler()
    exporter = LocalExporter(device_id)
    event_handler.add(exporter)

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.topic = mqtt_topic

    client.on_connect = event_handler.on_connect
    client.on_message = event_handler.on_message

    client.connect(mqtt_host, port=mqtt_port, keepalive=keep_alive)

    # ループ
    client.loop_forever()