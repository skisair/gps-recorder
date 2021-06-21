import paho.mqtt.client as mqtt
import json
import time

HOST = 'localhost'
PORT = 1883
KEEP_ALIVE = 60
TOPIC = 'sensor/device/GPRMC'
MESSAGE = {"data_id": "GPRMC", "lat": 99.0, "lon": 99.0 }

if __name__ == '__main__':
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.connect(HOST, port=PORT, keepalive=KEEP_ALIVE)
    message = MESSAGE
    for i in range(10):
        message['lat'] = message['lat'] + (float(i)/10.0)
        message['lon'] = message['lon'] - (float(i)/10.0)
        client.publish(TOPIC, json.dumps(message))
        time.sleep(1)

    client.disconnect()
