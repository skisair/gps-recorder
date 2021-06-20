import os
import logging
from datetime import datetime, timezone, timedelta

import paho.mqtt.client as mqtt
import time

LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)

HOST = 'localhost'
PORT = 1883
KEEP_ALIVE = 60
TOPIC = 'gps/sensor_data'

def on_connect(client, userdata, flags, respons_code):
    print('status {0}'.format(respons_code))
    client.subscribe(client.topic)


def on_message(client, userdata, message):
    logger.info(f'{datetime.now(JST).isoformat()} : {message.topic} {message.payload.decode()}')


if __name__ == '__main__':

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.topic = TOPIC

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(HOST, port=PORT, keepalive=KEEP_ALIVE)

    # ループ
    # client.loop_forever()
    time.sleep(3600)
