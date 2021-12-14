import os
import logging
import json
import time
from datetime import timezone, timedelta
import traceback
import threading
import socketio
import asyncio

import serial
import struct

LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

SERIAL_PORT = os.environ.get('SERIAL_PORT', default='/dev/serial0')
BAUD_RATE = int(os.environ.get('BAUD_RATE', default='9600'))
SIGNAL_INTERVAL = int(os.environ.get('SIGNAL_INTERVAL', default='10')) / 1000.0


JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


class SerialController:
    """
    MQTTへSubscribeし、ステータス通知にしたがって変数を変更
    シリアルへは常時指定間隔で信号を送信
    """

    NEUTRAL = 0
    MOVE_FORWARD = 2
    MOVE_BACKWARD = 1
    TURN_LEFT = 2
    TURN_RIGHT = 1

    BOOT = 54

    SPEED_LOW = 0
    SPEED_HIGH = 5

    __instance = None
    __thread = None
    sio = None
    __con = None

    @staticmethod
    def get_instance(port: str = SERIAL_PORT, baud_rate: int = BAUD_RATE, loop = None):
        if SerialController.__instance is None:
            SerialController(port=port, baud_rate=baud_rate)
        return SerialController.__instance

    def __init__(self, port: str = SERIAL_PORT, baud_rate: int = BAUD_RATE, loop = None):

        if SerialController.__instance is not None:
            raise Exception('use get_instance.')
        else:
            SerialController.__instance = self

        self._serial = serial.Serial(port)
        self._serial.baudrate = baud_rate
        self._serial.parity = serial.PARITY_NONE
        self._serial.bytesize = serial.EIGHTBITS
        self._serial.stopbits = serial.STOPBITS_ONE
        self._serial.timeout = 1

        self.switch_fb = SerialController.NEUTRAL
        self.switch_lr = SerialController.NEUTRAL
        self.dial_speed = SerialController.SPEED_LOW
        self.switch_boot = SerialController.NEUTRAL

        self.running = True
        self.loop = loop

        SerialController.__thread = threading.Thread(target=self.run)
        SerialController.__thread.daemon = True
        SerialController.__thread.start()

        print(f'connected to serial')

    def on_connect(self, client, userdata, flags, respons_code):
        print(f'connected to mqtt server:{respons_code}')

    def on_message(self, client, userdata, message):
        topic = message.topic
        data = message.payload.decode()
        print(f'{topic} : {data}')
        json_message = json.loads(data)
        self.set_signal(json_message)

    def set_signal(self, json_message):
        # print(f'serial:{json_message}')
        self.switch_fb = json_message['switch_fb']
        self.switch_lr = json_message['switch_lr']
        self.dial_speed = json_message['dial_speed']
        self.switch_boot = json_message['switch_boot']

    def disp_signal(self):
        d = self.calc_signal()
        return ('000000' + bin(d)[2:])[-6:]

    def send_signal(self):
        try:
            d = self.calc_signal()
            # print(f'serial:{d} / {self.switch_boot},{self.switch_fb},{self.switch_lr},{self.dial_speed}')
            data = struct.pack('B', d)
            self._serial.write(data)
            message = {
                'signal': ('000000' + bin(d)[2:])[-6:],
            }
            SerialController.sio.emit('signal', message, namespace='/web-ctl')
        except Exception as e:
            logging.info(f'self.switch_fb:{self.switch_fb} self.switch_lr:{self.switch_lr} self.dial_speed:{self.dial_speed}')
            logging.error(traceback.format_exc())
            logging.error(f'Serial Error:{e}')

    def calc_signal(self):
        # 右の３速：(0*3 + 1) * 6 + 3 = 9
        d = max(self.switch_boot, (self.switch_fb * 3 + self.switch_lr) * 6 + self.dial_speed)
        return d

    def stop(self):
        self.running = False

    def run(self):
        SerialController.sio = socketio.Client()
        while True:
            try:
                SerialController.sio.connect('ws://localhost:8081', namespaces=['/web-ctl'])
                break
            except Exception as e:
                print(e)
                time.sleep(1)

        while self.running:
            start_time = time.perf_counter()
            self.send_signal()
            end_time = time.perf_counter()
            sleep_time = SIGNAL_INTERVAL - (end_time - start_time)
            if sleep_time > 0:
                time.sleep(sleep_time)


class DummySerialController(SerialController):

    __instance = None

    @staticmethod
    def get_instance(port: str = SERIAL_PORT, baud_rate: int = BAUD_RATE, loop = None):
        if DummySerialController.__instance is None:
            DummySerialController(port=port, baud_rate=baud_rate, loop=loop)
        return DummySerialController.__instance

    def __init__(self, port: str = SERIAL_PORT, baud_rate: int = BAUD_RATE, loop = None):

        DummySerialController.__instance = self

        self.switch_fb = SerialController.NEUTRAL
        self.switch_lr = SerialController.NEUTRAL
        self.dial_speed = SerialController.SPEED_LOW
        self.switch_boot = SerialController.NEUTRAL
        self.loop = loop

        self.running = True

        SerialController.__thread = threading.Thread(target=self.run)
        SerialController.__thread.daemon = True
        SerialController.__thread.start()

        print('init')

    def send_signal(self):
        d = max(self.switch_boot, (self.switch_fb * 3 + self.switch_lr) * 6 + self.dial_speed)
        message = {
            'signal': ('000000' + bin(d)[2:])[-6:],
        }
        try:
            SerialController.sio.emit('signal', message, namespace='/web-ctl')
        except Exception as e:
            print(e)
            print('Emit fail')
        # 右の３速：(0*3 + 1) * 6 + 3 = 9
        # print(f'serial:{d} / {self.switch_boot},{self.switch_fb},{self.switch_lr},{self.dial_speed}')
        pass
