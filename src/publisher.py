import paho.mqtt.client as mqtt

HOST = 'localhost'
PORT = 1883
KEEP_ALIVE = 60
TOPIC = 'gps/sensor_data'
MESSAGE = '{"data_id": "GPGSA", "mode": "A", "type": "3", "satellite_01": "19", "satellite_02": "06", "satellite_03": "09", "satellite_04": "17", "satellite_05": "04", "satellite_06": "02", "satellite_07": "07", "satellite_08": "", "satellite_09": "", "satellite_10": "", "satellite_11": "", "satellite_12": "", "pdop": 2.24, "hdop": 1.42, "vdop": 1.73, "device_id": "ShoheinoAir-2", "local_time": "20210619165705743141"}'

if __name__ == '__main__':
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.connect(HOST, port=PORT, keepalive=KEEP_ALIVE)

    client.publish(TOPIC, MESSAGE)
    client.disconnect()
