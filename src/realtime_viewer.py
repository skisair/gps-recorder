import os
import logging
import json
import base64
from datetime import datetime, timezone, timedelta

import paho.mqtt.client as mqtt
import cv2
import numpy as np


LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


class ViewerEventHandler:

    def __init__(self):
        self.exporters = []
        self.latlon = str((0.0,0.0))

    def add(self, exporter):
        self.exporters.append(exporter)

    def on_connect(self, client, userdata, flags, respons_code):
        logger.info(f'connected to mqtt server:{respons_code}')
        client.subscribe(client.topic)

    def on_message(self, client, userdata, message):
        data = message.payload.decode()
        logger.debug(f'{message.topic} {data}')
        org_message = json.loads(data)
        data_id = org_message['data_id']
        if data_id == 'CAM01':
            jpg_as_text = org_message['image'].encode()
            jpg_original = base64.b64decode(jpg_as_text)
            jpg_as_np = np.frombuffer(jpg_original, dtype=np.uint8)
            image_buffer = cv2.imdecode(jpg_as_np, cv2.IMREAD_COLOR)
            b,g,r = 0, 255, 0
            position = (75, 75)
            image_buffer = cv2.putText(image_buffer,
                                       self.latlon,
                                       position,
                                       cv2.FONT_HERSHEY_SIMPLEX,
                                       2, (b,g,r), 2, cv2.LINE_AA)
            cv2.imshow('Image', image_buffer)
            cv2.waitKey(1)
        elif data_id == 'GPRMC':
            lat = org_message['lat']
            lon = org_message['lon']
            self.latlon = str((lat,lon))
            print(self.latlon)


if __name__ == '__main__':

    device_id = os.environ.get('DEVICE_ID')
    mqtt_host = os.environ.get('MQTT_HOST', default='localhost')
    mqtt_port = int(os.environ.get('MQTT_PORT', default=1883))
    keep_alive = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))
    subscribe_mqtt_topic = os.environ.get('MQTT_TOPIC', default='sensor/#')

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.topic = subscribe_mqtt_topic

    event_handler = ViewerEventHandler()

    client.on_connect = event_handler.on_connect
    client.on_message = event_handler.on_message

    client.connect(mqtt_host, port=mqtt_port, keepalive=keep_alive)

    # ループ
    client.loop_forever()
