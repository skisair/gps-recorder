import os
import platform
import logging
from datetime import datetime, timezone, timedelta
import time
import json
import base64
import argparse

from exporter import LocalExporter, MqttExporter

import cv2
import paho.mqtt.client as mqtt


DEVICE_ID = os.environ.get('DEVICE_ID', default=platform.uname()[1])
LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)
CAMERA_ID = int(os.environ.get('CAMERA_ID', default=0))
TARGET_WIDTH = int(os.environ.get('TARGET_WIDTH', default=640))
DATA_ID = os.environ.get('DATA_ID', default='CAM01')
SEND_INTERVAL = int(os.environ.get('SEND_INTERVAL', default=1000))

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


class CameraDevice:
    def __init__(self, device_id: str, data_id:str):
        self.capture = cv2.VideoCapture(CAMERA_ID)
        self.device_id = device_id
        self.data_id = data_id
        self.running = True
        self.exporters = []
        self.latlon = str((0.0,0.0))
        self.headless = True
        self.client = None

    def run_mqtt(self):
        mqtt_host = os.environ.get('MQTT_HOST', default='localhost')
        mqtt_port = int(os.environ.get('MQTT_PORT', default=1883))
        keep_alive = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))
        subscribe_mqtt_topic = os.environ.get('MQTT_TOPIC', default='sensor/#')
        client = mqtt.Client(protocol=mqtt.MQTTv311)
        client.topic = subscribe_mqtt_topic

        client.on_connect = self.on_connect
        client.on_message = self.on_message

        client.connect(mqtt_host, port=mqtt_port, keepalive=keep_alive)
        self.client = client
        self.headless = False

    def add(self, exporter):
        """
        出力処理の追加
        :param exporter:
        :return:
        """
        self.exporters.append(exporter)

    def on_connect(self, client, userdata, flags, respons_code):
        logger.info(f'connected to mqtt server:{respons_code}')
        client.subscribe(client.topic)

    def on_message(self, client, userdata, message):
        data = message.payload.decode()
        logger.debug(f'{message.topic} {data}')
        org_message = json.loads(data)
        data_id = org_message['data_id']
        if data_id == 'GPRMC':
            lat = org_message['lat']
            lon = org_message['lon']
            self.latlon = str((lat,lon))
            print(self.latlon)

    def run(self):
        last_send_time = 0
        while self.running:
            date_time = datetime.now(JST).strftime('%Y%m%d%H%M%S%f')
            shoot_time = time.time()

            resized_image, size = self.get_image()

            retval, buffer = cv2.imencode('.png', resized_image)
            jpg_as_text = base64.b64encode(buffer).decode()
            message = {
                'data_id': self.data_id, 'image': jpg_as_text, 'size': str(size), 'format': 'png', 'device_id': self.device_id,
                'local_time': date_time}
            logger.debug(message)
            self._output(message)
            sleep_seconds = (SEND_INTERVAL - (time.time() - shoot_time)) / 1000.0
            print(len(jpg_as_text),sleep_seconds)

            if self.headless:
                time.sleep(sleep_seconds)
            else:
                while ((SEND_INTERVAL - (time.time() - shoot_time)) / 1000.0) > 0:
                    b,g,r = 0, 255, 0
                    position = (75, 75)
                    resized_image = cv2.putText(resized_image,
                                               self.latlon,
                                               position,
                                               cv2.FONT_HERSHEY_SIMPLEX,
                                               2, (b, g, r), 2, cv2.LINE_AA)
                    cv2.imshow('Image', resized_image)
                    cv2.waitKey(1)
                    resized_image, size = self.get_image()
                    self.client.loop(0)


        self.capture.release()

    def get_image(self):
        ret, image = self.capture.read()
        height, width = image.shape[:2]
        resize_rate = TARGET_WIDTH / width
        size = (TARGET_WIDTH, int(height * resize_rate))
        resized_image = cv2.resize(image, size)
        return resized_image, size

    def _output(self, message):
        for exporter in self.exporters:
            try:
                exporter.export(message)
            except Exception as e:
                logger.error(f'output fail {exporter}/{message} : {e}')

    def stop(self):
        self.running = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--viewer', help='viewer', action='store_true')
    args = parser.parse_args()
    print(args.viewer)

    device_id = DEVICE_ID
    data_id = DATA_ID
    local_exporter = LocalExporter(device_id)
    mqtt_exporter = MqttExporter(device_id)

    camera = CameraDevice(device_id, data_id)
    camera.add(local_exporter)
    camera.add(mqtt_exporter)
    if args.viewer:
        camera.run_mqtt()

    camera.run()