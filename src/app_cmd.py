import os
import sys
import platform
import logging
from datetime import datetime, timezone, timedelta

from gps_device import GpsDevice
from util.exporter import QueueExporter, LocalExporter

GPS_PORT = os.environ.get('GPS_PORT', default='/dev/tty.usbmodem14101')
DEVICE_ID = os.environ.get('DEVICE_ID', default=platform.uname()[1])
LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)
# self.output_folder = os.environ.get('OUTPUT_FOLDER', default='data/${device_id}')
# self.output_folder = Template(self.output_folder).substitute(device_id=device_id, **os.environ)
# self.output_folder_format = os.environ.get('OUTPUT_FOLDER_FORMAT', default='%Y/%m/%d/%H')
# self.output_file_format = os.environ.get('OUTPUT_FILE_FORMAT', default='%Y%m%d%H%M%S%f-${data_id}-${id}.json')


JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


def fork():
    pid = os.fork()
    if pid > 0:
        f = open('gps_device.pid','w')
        f.write(str(pid)+"\n")
        f.close()
        sys.exit()

    if pid == 0:
        device_id = DEVICE_ID
        port = GPS_PORT

        print(f'device_id:{device_id}')
        print(f'port:{port}')
        device = GpsDevice(device_id, port)

        local_exporter = LocalExporter(device_id)
        device.add(local_exporter)

        device.run()

if __name__ == '__main__':
    fork()