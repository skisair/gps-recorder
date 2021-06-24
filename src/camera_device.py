import os
import platform
import logging
from datetime import datetime, timezone, timedelta
import time
import json
import base64
import argparse
from string import Template

from exporter import LocalExporter, MqttExporter

import cv2
import paho.mqtt.client as mqtt


DEVICE_ID = os.environ.get('DEVICE_ID', default=platform.uname()[1])
LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)
CAMERA_ID = int(os.environ.get('CAMERA_ID', default=0))
TARGET_WIDTH = int(os.environ.get('TARGET_WIDTH', default=640))
DATA_ID = os.environ.get('DATA_ID', default='CAM01')
SEND_INTERVAL = int(os.environ.get('SEND_INTERVAL', default=1000))
DEVICE_EXPORTER = os.environ.get('DEVICE_EXPORTER', default='LOCAL,MQTT')

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
        self.latlon = (0.0,0.0)
        self.headless = True
        self.client = None

    def run_mqtt(self):
        mqtt_host = os.environ.get('MQTT_HOST', default='localhost')
        mqtt_port = int(os.environ.get('MQTT_PORT', default=1883))
        keep_alive = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))
        subscribe_mqtt_topic = os.environ.get('MQTT_TOPIC', default='sensor/#')
        subscribe_mqtt_topic = Template(subscribe_mqtt_topic).safe_substitute(device_id=self.device_id, **os.environ)
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
            self.latlon = (lat,lon)
            print(self.latlon)

    def run(self):
        last_send_time = 0
        user_input = 'key:'
        recording = True
        while self.running:
            date_time = datetime.now(JST).strftime('%Y%m%d%H%M%S%f')
            shoot_time = time.time()

            resized_image, size = self.get_image()

            retval, buffer = cv2.imencode('.png', resized_image)
            jpg_as_text = base64.b64encode(buffer).decode()
            message = {
                'data_id': self.data_id, 'image': jpg_as_text, 'size': str(size), 'format': 'png', 'device_id': self.device_id,
                'local_time': date_time}
            # logger.debug(message)
            if recording:
                logger.debug(f'send message. device_id:{self.device_id} data_id:{self.data_id} size:{str(size)} len:{len(jpg_as_text)}')
                self._output(message)
            sleep_seconds = (SEND_INTERVAL/1000.0 - (time.time() - shoot_time))

            if self.headless:
                time.sleep(sleep_seconds)
            else:
                while (SEND_INTERVAL/1000.0 - (time.time() - shoot_time)) > 0:
                    # print(SEND_INTERVAL/1000.0 - (time.time() - shoot_time))
                    color_bgr = (0, 255, 0)
                    position = (75, 75)
                    font_size = 1.5
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    message = 'lat: ' + str(self.latlon[0])
                    resized_image = cv2.putText(resized_image, message, position, font,
                                                font_size, color_bgr, 2, cv2.LINE_AA)
                    position = (75, 150)
                    message = 'lon: ' + str(self.latlon[1])
                    resized_image = cv2.putText(resized_image, message, position, font,
                                                font_size, color_bgr, 2, cv2.LINE_AA)

                    position = (75, 450)
                    font_size = 1
                    if recording:
                        message = 'Press [S] to stop recording'
                    else:
                        message = 'Press [R] to record'

                    resized_image = cv2.putText(resized_image, message, position, font,
                                                font_size, color_bgr, 2, cv2.LINE_AA)

                    cv2.imshow('Image', resized_image)
                    key = cv2.waitKey(1)
                    if key == -1:
                        pass
                    elif key == 0x72:
                        logger.info('Start recording')
                        recording = True
                    elif key == 0x73:
                        logger.info('Stop recording')
                        recording = False
                    else:
                        pass

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
        self.capture.release()
        self.running = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--viewer', help='viewer', action='store_true')
    args = parser.parse_args()
    print(args.viewer)

    device_id = DEVICE_ID
    data_id = DATA_ID
    device_exporter = DEVICE_EXPORTER.split(',')

    device = None

    while True:
        try:
            device = CameraDevice(device_id, data_id)

            if 'LOCAL' in device_exporter:
                local_exporter = LocalExporter(device_id)
                device.add(local_exporter)
            if 'MQTT' in device_exporter:
                mqtt_exporter = MqttExporter(device_id)
                device.add(mqtt_exporter)
                if args.viewer:
                    device.run_mqtt()

            try:
                device.run()
            except KeyboardInterrupt:
                device.stop()
                break
        except Exception as e:
            if device is not None:
                device.stop()
            logger.error(f'LOOP : {e}')
            time.sleep(1)
