import os
import platform
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import math
import traceback

import serial

from util.exporter import LocalExporter, MqttExporter, QueueExporter

# Macの場合、 /dev/tty.usbserial-* の形で認識される。WindowsならCOM3とかCOM4とかになるはず
# ls /dev/tty.usbserial* で出てきたポート名を入れること

GPS_PORT = os.environ.get('GPS_PORT', default='/dev/tty.usbmodem14101')
DEVICE_ID = os.environ.get('DEVICE_ID', default=platform.uname()[1])
LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)
DUMMY_SCRIPT = os.environ.get('DUMMY_SCRIPT', default='')  # dummy/gps/gps-sample001.txt
DEVICE_EXPORTER = os.environ.get('DEVICE_EXPORTER', default='LOCAL,MQTT')
TARGET_DATA_ID = os.environ.get('TARGET_DATA_ID', default='GPRMC,GPGGA,GPVTG,GPGSA,GPGSV,GPGLL,GPTXT')
EXCLUDE_DATA_ID = os.environ.get('EXCLUDE_DATA_ID', default='')

'''
GPRMC,GPGGA,GPVTG,GPGSA,GPGSV,GPGLL,GPTXT
'''

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


class SerialPort:
    """
    シリアル通信モジュール
    （特にGPSというわけではない…）
    """

    def __init__(self, port: str, baudrate: int = 9600, parity: str = serial.PARITY_NONE, bytesize: int = serial.EIGHTBITS,stopbits: float = serial.STOPBITS_ONE, timeout = None, xonxoff: int = 0, rtscts: int = 0):
        """
        初期化
        :param port:
        :param baudrate:
        :param parity:
        :param bytesize:
        :param stopbits:
        :param xonxoff:
        :param rtscts:
        """
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=parity,
            bytesize=bytesize,
            stopbits=stopbits,
            timeout=timeout,
            xonxoff=xonxoff,
            rtscts=rtscts,
        )

    def read(self) -> str:
        """
        情報読み込み
        :return:
        """
        try:
            gps_raw_data = self.ser.readline().decode('utf-8')
        except UnicodeDecodeError as e:
            print(e)
            return ''
        except serial.serialutil.SerialException as e:
            print(e)
            return ''

        return gps_raw_data

    def close(self):
        self.ser.close()

class DummySerialPort:
    """
    ダミーシリアル通信
    """
    # ファイルから読み込み、一連の読み込み後、返却スリープあり、ファイルの終端まできたら繰り返し

    def __init__(self, path:str):
        with open(path, mode='r') as file:
            self.lines = file.readlines()
        self.line_index = 0

    def _next(self):
        """
        ファイルの１行を返却する
        :return:
        """
        if self.line_index >= len(self.lines):
            self.line_index = 0
        line = self.lines[self.line_index]
        self.line_index = self.line_index + 1
        return line

    def read(self):
        """
        スクリプト解釈・応答返却
        :return:
        """
        while True:
            # 空白・改行は削除
            next_line = self._next().strip()
            if len(next_line) == 0:
                # 空行はパス
                continue
            if next_line.startswith('#'):
                # コメント行はパス
                continue
            elif next_line.startswith('sleep'):
                # sleep XXXX はXXX秒スリープ
                # sleep のみであれば１秒
                # スリープ後は次の行を読み込み
                values = next_line.split(' ')
                if len(values) == 1:
                    sleep_time = 1
                else:
                    sleep_time = int(values[1])
                time.sleep(sleep_time)
            else:
                # その他は、シリアルの応答として返却
                break

        next_line = datetime.utcnow().strftime(next_line)
        return next_line


class GpsDevice:
    def __init__(self, device_id: str, port: str,
                 baudrate: int = 9600, parity: str = serial.PARITY_NONE, bytesize: int = serial.EIGHTBITS,
                 stopbits: float = serial.STOPBITS_ONE, xonxoff: int = 0, rtscts: int = 0, dummy_script: str = ''):
        """
        GPSトラッカー
        :param device_id:
        :param port:
        :param baudrate:
        :param parity:
        :param bytesize:
        :param stopbits:
        :param xonxoff:
        :param rtscts:
        :param dummy_script: ダミー処理用スクリプト
        """
        self.device_id = device_id
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.running = True
        if len(dummy_script) > 0:
            self.sensor = DummySerialPort(dummy_script)
        else:
            self.sensor = SerialPort(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                bytesize=self.bytesize,
                stopbits=self.stopbits,
                timeout=None,
                xonxoff=self.xonxoff,
                rtscts=self.rtscts,
            )

        self.exporters = []
        self.check_target_data_id = False
        self.target_data_ids = []
        self.check_exclude_data_id = False
        self.exclude_data_ids = []

    def set_target_data_ids(self, target_data_ids):
        self.check_target_data_id = True
        self.target_data_ids = target_data_ids

    def set_exclude_data_ids(self, exclude_data_ids):
        self.check_exclude_data_id = True
        self.exclude_data_ids = exclude_data_ids

    def add(self, exporter):
        """
        出力処理の追加
        :param exporter:
        :return:
        """
        self.exporters.append(exporter)

    def run(self):
        while self.running:
            gps_raw_data = self.sensor.read()
            gps_raw_data = gps_raw_data.replace('\x00', '')
            try:
                gps_data, check_sum = gps_raw_data.split('*')
                gps_data = gps_data.split(',')
                messages = self._parse(gps_data)
                for message in messages:
                    date_time = datetime.now(JST).strftime('%Y%m%d%H%M%S%f')
                    message['device_id'] = self.device_id
                    message['local_time'] = date_time
                    logger.debug(message)
                    self._output(message)
            except ValueError:
                pass
                '''
                self.sensor.close()
                self.sensor = SerialPort(
                    port=self.port,
                    baudrate=self.baudrate,
                    parity=self.parity,
                    bytesize=self.bytesize,
                    stopbits=self.stopbits,
                    timeout=None,
                    xonxoff=self.xonxoff,
                    rtscts=self.rtscts,
                )
                '''

    @staticmethod
    def parse_matrix_value(input: str) -> float:
        input = float(input)
        top = math.floor(input/100)
        bottom = (input - top*100) / 60.0
        return top + bottom
        # 3655.9461は、36°+55.9461′だから、36+(55.9461/60)=36.932435

    def _parse(self, values: List) -> List[Dict]:
        """
        データIDに基づく解析処理の分岐
        :param values:
        :return:
        """
        result = []
        data_id = values[0][1:]
        if self.check_target_data_id and (data_id not in self.target_data_ids) :
            logger.debug(f'{data_id}: not in target_data_ids:{self.target_data_ids}')
            return result
        elif self.check_exclude_data_id and (data_id in self.exclude_data_ids):
            logger.debug(f'{data_id}: in exclude_data_ids:{self.exclude_data_ids}')
            return result

        try:
            if data_id == 'GNRMC':
                self._parse_GNRMC(data_id, values, result)
            elif data_id == 'GPRMC':
                self._parse_GPRMC(data_id, values, result)
            elif data_id == 'GPGGA':
                self._parse_GPGGA(data_id, values, result)
            elif data_id == 'GNVTG':
                self._parse_GPVTG(data_id, values, result)
            elif data_id == 'GPVTG':
                self._parse_GPVTG(data_id, values, result)
            elif data_id == 'GPGSA':
                self._parse_GPGSA(data_id, values, result)
            elif data_id == 'GNGSA':
                self._parse_GPGSA(data_id, values, result)
            elif data_id == 'GNGSV':
                self._parse_GPGSV(data_id, values, result)
            elif data_id == 'GPGSV':
                self._parse_GPGSV(data_id, values, result)
            elif data_id == 'GNGLL':
                self._parse_GPGLL(data_id, values, result)
            elif data_id == 'GPGLL':
                self._parse_GPGLL(data_id, values, result)
            elif data_id == 'GPTXT':
                logger.info(f'message from device : {" ".join(values)}')
            elif data_id == 'GNTXT':
                logger.info(f'message from device : {" ".join(values)}')
            else:
                logger.warning(f'data_id {data_id} is not supported : {values}')
        except Exception as e:
            logger.error(f'parse error in data_id:{data_id} values:{values} : {e}')

        return result

    def _parse_GPGLL(self, data_id, values, result):
        """
        GPGLLの解析
        :param data_id:
        :param values:
        :param result:
        :return:
        """
        utc_date = datetime.utcnow().strftime('%d%m%y')
        utc_time = values[5]
        try:
            gps_date_time = datetime.strptime(utc_date + utc_time, '%d%m%y%H%M%S.%f').isoformat()
        except ValueError:
            logger.warning(f'date format error in GPRMC {values}')
            gps_date_time = datetime.now().isoformat()

        warning = values[6]
        if warning == 'V':
            logger.warning(f'GPGGA staus is V.')
        else:
            lat = self.parse_matrix_value(values[1])
            lon = self.parse_matrix_value(values[3])
            lat_d = values[2]
            lon_d = values[4]
            if lat_d == 'S':
                lat = -lat
            if lon_d == 'W':
                lon = -lon
            message = {
                'data_id': data_id,
                'gps_date_time': gps_date_time,
                'lat': lat,
                # 'lat_d': values[2],
                'lon': lon,
                # 'lon_d': values[4],
                # 'utc_time': values[5],
                # 'warning': values[6],
                'mode': values[7],
            }
            result.append(message)

    def _parse_GPGSV(self, data_id, values, result):
        """
        GPGSVの解析
        :param data_id:
        :param values:
        :param result:
        :return:
        """
        total_messages = int(values[1])
        message_number = int(values[2])
        total_sv = int(values[3])
        for sv_in_message in range(4):
            sv_num = ((message_number - 1) * 4 + sv_in_message + 1)
            if sv_num > total_sv:
                break
            message = {
                'data_id': data_id,
                # 'total_messages': total_messages,
                # 'message_number': message_number,
                'total_sv': total_sv,
                'sv_num': sv_num,
                # 'sv_in_message': sv_in_message,
                'sv_prn': values[4 + sv_in_message * 4],
                'el_degree': int(values[5 + sv_in_message * 4]),
                'az_degree': int(values[6 + sv_in_message * 4]),
            }
            srn = values[7 + sv_in_message * 4]
            if len(srn) > 0:
                message['srn'] = int(srn)
            else:
                message['srn'] = 0
            result.append(message)

    def _parse_GPGSA(self, data_id, values, result):
        """
        GPGSA電文の解析
        :param data_id:
        :param values:
        :param result:
        :return:
        """
        if len(values[3]) == 0:
            logger.warning(f'no satellites in GPGSA')
        else:
            message = {
                'data_id': data_id,
                'mode': values[1],
                'type': values[2],
                'satellite_01': values[3],
                'satellite_02': values[4],
                'satellite_03': values[5],
                'satellite_04': values[6],
                'satellite_05': values[7],
                'satellite_06': values[8],
                'satellite_07': values[9],
                'satellite_08': values[10],
                'satellite_09': values[11],
                'satellite_10': values[12],
                'satellite_11': values[13],
                'satellite_12': values[14],
                'pdop': float(values[15]),
                'hdop': float(values[16]),
                'vdop': float(values[17]),
            }
            result.append(message)

    def _parse_GPVTG(self, data_id, values, result):
        if len(values[5]) == 0:
            logger.warning(f'no data in GPVTG')
        else:
            message = {
                'data_id': data_id,
                'course': values[1],
                # 'true_course': values[2],
                'm_course': values[3],
                # 'mag_course': values[4],
                # 'k_speed': values[5],
                # 'speed_k_unit': values[6],
                'speed': float(values[7]),
                # 'speed_m_unit': values[8],
                'mode': values[9],
            }
            result.append(message)

    def _parse_GPGGA(self, data_id, values, result):
        """
        GPGGAの解析
        :param data_id:
        :param values:
        :param result:
        :return:
        """
        utc_date = datetime.utcnow().strftime('%d%m%y')
        utc_time = values[1]
        try:
            gps_date_time = datetime.strptime(utc_date + utc_time, '%d%m%y%H%M%S.%f').isoformat()
        except ValueError:
            logger.warning(f'date format error in GPRMC {values}')
            gps_date_time = datetime.now().isoformat()

        lat = values[2]
        if lat == '':
            logger.warning(f'GPGGA is not valid.')
        else:
            lat = self.parse_matrix_value(values[2])
            lon = self.parse_matrix_value(values[4])
            lat_d = values[3]
            lon_d = values[5]
            if lat_d == 'S':
                lat = -lat
            if lon_d == 'W':
                lon = -lon
            message = {
                'data_id': data_id,
                'gps_date_time': gps_date_time,
                'lat': lat,
                'lon': lon,
                'fix_quality': int(values[6]),
                'num_satellites': int(values[7]),
                'hdop': float(values[8]),
                'altitude': float(values[9]),
                # 'alt_m': values[10],
                'geoid_height': float(values[11]),
                # 'geo_m': values[12],
            }
            if len(values[13]) > 0:
                message['dgps_update'] = values[13]
                message['dgps_id'] = values[14]
            result.append(message)

    def _parse_GNRMC(self, data_id, values, result):
        """
        GNRMCの解析
        :param data_id:
        :param values:
        :param result:
        :return:
        """
        warning = values[2]
        utc_time = values[1]
        utc_date = values[9]
        try:
            gps_date_time = datetime.strptime(utc_date + utc_time, '%d%m%y%H%M%S.%f').isoformat()
        except ValueError:
            logger.warning(f'date format error in GNRMC {values}')
            gps_date_time = datetime.now().isoformat()
        if warning == 'A':
            lat = self.parse_matrix_value(values[3])
            lon = self.parse_matrix_value(values[5])
            lat_d = values[4]
            lon_d = values[6]
            if lat_d == 'S':
                lat = -lat
            if lon_d == 'W':
                lon = -lon
            speed = float(values[7])
            message = {
                'data_id': data_id,
                'gps_date_time': gps_date_time,
                # 'warning': warning,
                'lat': lat,
                'lon': lon,
                'speed': speed,
                'mode': values[12],
            }
            if len(values[8]) > 0:
                message['course'] = float(values[8])
            if len(values[10]) > 0:
                variation = float(values[10])
                if values[11] == 'S':
                    variation = -variation
                message['variation'] = variation

            result.append(message)
        else:
            logger.warning(f'GNRMC status is in V. values:{values}')

    def _parse_GPRMC(self, data_id, values, result):
        """
        GPRMCの解析
        :param data_id:
        :param values:
        :param result:
        :return:
        """
        warning = values[2]
        utc_time = values[1]
        utc_date = values[9]
        try:
            gps_date_time = datetime.strptime(utc_date + utc_time, '%d%m%y%H%M%S.%f').isoformat()
        except ValueError:
            logger.warning(f'date format error in GPRMC {values}')
            gps_date_time = datetime.now().isoformat()
        if warning == 'A':
            lat = self.parse_matrix_value(values[3])
            lon = self.parse_matrix_value(values[5])
            lat_d = values[4]
            lon_d = values[6]
            if lat_d == 'S':
                lat = -lat
            if lon_d == 'W':
                lon = -lon
            speed = float(values[7])
            message = {
                'data_id': data_id,
                'gps_date_time': gps_date_time,
                # 'warning': warning,
                'lat': lat,
                'lon': lon,
                'speed': speed,
                'mode': values[12],
            }
            if len(values[8]) > 0:
                message['course'] = float(values[8])
            if len(values[10]) > 0:
                variation = float(values[10])
                if values[11] == 'S':
                    variation = -variation
                message['variation'] = variation

            result.append(message)
        else:
            logger.warning(f'GPRMC status is in V. values:{values}')

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
    device_exporter = DEVICE_EXPORTER.split(',')
    target_data_ids = TARGET_DATA_ID.split(',')
    exclude_data_ids = EXCLUDE_DATA_ID.split(',')
    device = None
    while True:
        try:
            device = GpsDevice(device_id, GPS_PORT, dummy_script=DUMMY_SCRIPT)
            if len(target_data_ids) > 0:
                device.set_target_data_ids(target_data_ids)
            elif len(exclude_data_ids) > 0:
                device.set_exclude_data_ids(exclude_data_ids)

            if 'LOCAL' in device_exporter:
                local_exporter = LocalExporter(device_id)
                device.add(local_exporter)
            if 'MQTT' in device_exporter:
                mqtt_exporter = MqttExporter(device_id)
                device.add(mqtt_exporter)
            if 'QUEUE' in device_exporter:
                queue_exporter = QueueExporter(device_id)
                device.add(queue_exporter)

            try:
                device.run()
            except KeyboardInterrupt:
                device.stop()
                break
        except Exception as e:
            logger.error(traceback.format_exc())
            if device is not None:
                device.stop()
            logger.error(f'LOOP : {e}')
            time.sleep(1)
