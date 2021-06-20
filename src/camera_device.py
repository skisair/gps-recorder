import os
import logging
from datetime import datetime, timezone, timedelta
import time
from typing import List, Dict

import time

from exporter import LocalExporter, MqttExporter

import cv2
import numpy as np
import base64

DEVICE_ID = os.environ.get('DEVICE_ID', default=os.uname()[1])
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

    def add(self, exporter):
        """
        出力処理の追加
        :param exporter:
        :return:
        """
        self.exporters.append(exporter)

    def run(self):
        last_send_time = 0
        while self.running:
            date_time = datetime.now(JST).strftime('%Y%m%d%H%M%S%f')
            shoot_time = time.time()
            ret, image = self.capture.read()
            height, width = image.shape[:2]
            resize_rate = TARGET_WIDTH/width
            size = (TARGET_WIDTH, int(height*resize_rate))
            resized_image = cv2.resize(image, size)
            retval, buffer = cv2.imencode('.png', resized_image)
            jpg_as_text = base64.b64encode(buffer).decode()
            message = {
                'data_id': self.data_id, 'image': jpg_as_text, 'size': str(size), 'format': 'png', 'device_id': self.device_id,
                'local_time': date_time}
            logger.debug(message)
            self._output(message)
            sleep_seconds = (SEND_INTERVAL - (time.time() - shoot_time)) / 1000.0
            print(len(jpg_as_text),sleep_seconds)
            time.sleep(sleep_seconds)

        self.capture.release()

    def _output(self, message):
        for exporter in self.exporters:
            try:
                exporter.export(message)
            except Exception as e:
                logger.error(f'output fail {exporter}/{message} : {e}')

    def stop(self):
        self.running = False


if __name__ == '__main__':
    device_id = DEVICE_ID
    data_id = DATA_ID
    local_exporter = LocalExporter(device_id)
    mqtt_exporter = MqttExporter(device_id)

    camera = CameraDevice(device_id, data_id)
    camera.add(local_exporter)
    camera.add(mqtt_exporter)
    camera.run()