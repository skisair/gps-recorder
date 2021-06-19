import os
import logging
import json
import uuid
from string import Template
from datetime import datetime, timezone, timedelta
from typing import List, Dict

import serial

# Macの場合、 /dev/tty.usbserial-* の形で認識される。WindowsならCOM3とかCOM4とかになるはず
# ls /dev/tty.usbserial* で出てきたポート名を入れること

GPS_PORT = os.environ.get('GPS_PORT', default='/dev/tty.usbmodem14101')
DEVICE_ID = os.environ.get('DEVICE_ID', default=os.uname()[1])
LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)


class LocalExporter:
    """
    ローカル出力クラス
    """

    def __init__(self, device_id: str):
        """
        環境変数
        OUTPUT_FOLDER : 出力先フォルダパス data/${device_id}
        OUTPUT_FOLDER_FORMAT : 出力先振分フォーマット %Y/%m/%d/%H
        OUTPUT_FILE_FORMAT : 出力ファイル名 %Y%m%d%H%M%S%f-${id}.json
        (idはuuidにより一意な値を入れ、重複を防ぐ）
        :param device_id: デバイスID
        """
        self.device_id = device_id
        # 出力フォルダの設定作成
        self.output_folder = os.environ.get('OUTPUT_FOLDER', default='data/${device_id}')
        self.output_folder = Template(self.output_folder).substitute(device_id=device_id, **os.environ)
        self.output_folder_format = os.environ.get('OUTPUT_FOLDER_FORMAT', default='%Y/%m/%d/%H')
        self.output_file_format = os.environ.get('OUTPUT_FILE_FORMAT', default='%Y%m%d%H%M%S%f-${data_id}-${id}.json')
        os.makedirs(self.output_folder, exist_ok=True)

    def export(self, message):
        """
        メッセージの出力（フォルダにJSONで保存）
        :param message:
        :return:
        """
        unique_id = str(uuid.uuid4())
        output_string = json.dumps(message)
        if 'data_id' in message:
            data_id = message['data_id']
        else:
            data_id = '____'
        file_name = datetime.now(JST).strftime(
            Template(self.output_file_format).substitute(id=unique_id, device_id=device_id, data_id=data_id, **os.environ))
        folder = datetime.now(JST).strftime(
            Template(self.output_folder_format).substitute(id=unique_id, device_id=device_id, data_id=data_id, **os.environ))
        folder = os.path.join(self.output_folder, folder)
        os.makedirs(folder, exist_ok=True)
        with open(file=os.path.join(folder, file_name), mode='w', encoding='UTF-8') as f:
            f.write(output_string)


class GpsTracker:
    def __init__(self, device_id: str, port: str,
                 baudrate: int = 9600, parity: str = serial.PARITY_NONE, bytesize: int = serial.EIGHTBITS,
                 stopbits: float = serial.STOPBITS_ONE, xonxoff: int = 0, rtscts: int = 0):
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
        """
        self.device_id = device_id
        self.port = port
        self.running = True
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=parity,
            bytesize=bytesize,
            stopbits=stopbits,
            timeout=None,
            xonxoff=xonxoff,
            rtscts=rtscts,
        )
        self.exporters = []

    def add(self, exporter):
        """
        出力処理の追加
        :param exporter:
        :return:
        """
        self.exporters.append(exporter)

    def run(self):
        while self.running:
            gps_raw_data = self.ser.readline().decode('utf-8')
            gps_data, check_sum = gps_raw_data.split('*')
            gps_data = gps_data.split(',')
            # logger.debug(gps_data)
            messages = self._parse(gps_data)
            for message in messages:
                date_time = datetime.now(JST).strftime('%Y%m%d%H%M%S%f')
                message['device_id'] = self.device_id
                message['local_time'] = date_time
                logger.debug(message)
                self._output(message)

    def _parse(self, values: List) -> List[Dict]:
        """
        データIDに基づく解析処理の分岐
        :param values:
        :return:
        """
        result = []
        data_id = values[0][1:]
        try:
            if data_id == 'GPRMC':
                self._parse_GPRMC(data_id, values, result)
            elif data_id == 'GPGGA':
                self._parse_GPGGA(data_id, values, result)
            elif data_id == 'GPVTG':
                self._parse_GPVTG(data_id, values, result)
            elif data_id == 'GPGSA':
                self._parse_GPGSA(data_id, values, result)
            elif data_id == 'GPGSV':
                self._parse_GPGSV(data_id, values, result)
            elif data_id == 'GPGLL':
                self._parse_GPGLL(data_id, values, result)
            elif data_id == 'GPTXT':
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
            lat = float(values[1]) / 100.0
            lng = float(values[3]) / 100.0
            lat_d = values[2]
            lng_d = values[4]
            if lat_d == 'S':
                lat = -lat
            if lng_d == 'W':
                lng = -lng
            message = {
                'data_id': data_id,
                'gps_date_time': gps_date_time,
                'lat': lat,
                # 'lat_d': values[2],
                'lng': lng,
                # 'lng_d': values[4],
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
            lat = float(values[2]) / 100.0
            lng = float(values[4]) / 100.0
            lat_d = values[3]
            lng_d = values[5]
            if lat_d == 'S':
                lat = -lat
            if lng_d == 'W':
                lng = -lng
            message = {
                'data_id': data_id,
                'gps_date_time': gps_date_time,
                'lat': lat,
                'lng': lng,
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
            lat = float(values[3]) / 100.0
            lng = float(values[5]) / 100.0
            lat_d = values[4]
            lng_d = values[6]
            if lat_d == 'S':
                lat = -lat
            if lng_d == 'W':
                lng = -lng
            speed = float(values[7])
            message = {
                'data_id': data_id,
                'gps_date_time': gps_date_time,
                # 'warning': warning,
                'lat': lat,
                'lng': lng,
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
            logger.warning(f'GPRMC status is in V.')

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
    exporter = LocalExporter(device_id)
    gps = GpsTracker(device_id, GPS_PORT)
    gps.add(exporter)
    try:
        gps.run()
    except KeyboardInterrupt:
        gps.stop()
