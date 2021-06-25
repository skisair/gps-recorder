from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=+9), 'JST')


def list_device():
    """
    デバイス一覧を返却
    ・device_id: 機械ID
    ・device_name: 機械名
    ・last_communication_time: 最終通信時刻
    ・location:{lat: 緯度, lon: 経度}
    :return:
    """
    dummy_time = datetime.now(JST).isoformat()
    location = {
        'lat': 35.685241,
        'lon': 139.418968,
    }
    result = [
        {
            'device_id': 'DEVICE001',
            'device_name': 'Device 001',
            'last_communication_time': dummy_time,
            'location': location,
        },
        {
            'device_id': 'DEVICE002',
            'device_name': 'Device 002',
            'last_communication_time': dummy_time,
            'location': location,
        },
        {
            'device_id': 'DEVICE003',
            'device_name': 'Device 002',
            'last_communication_time': dummy_time,
            'location': location,
        },
    ]
    return result


def get_device(device_id:str):
    """
    デバイス情報を返却
    ・device_id: 機械ID
    ・device_name: 機械名
    ・last_communication_time: 最終通信時刻
    ・location:{lat: 緯度, lon: 経度}
    :param device_id:
    :return:
    """
    dummy_time = datetime.now(JST).isoformat()
    location = {
        'lat': 35.685241,
        'lon': 139.418968,
    }
    result = {
        'device_id': device_id,
        'device_name': 'DUMMY DEVICE NAME',
        'last_communication_time': dummy_time,
        'location': location,
    }
    return result


def list_reservation(device_id:str, from_time:datetime):
    """
    ・reservation_id: 予約ID
    ・device_id: デバイスID
    ・device_name: デバイス名
    ・start_time: 予約開始時間
    ・end_time: 予約終了時間
    ・reserver_id: 予約者ID
    ・reserver_name: 予約者名
    :param device_id: デバイスID
    :param from_time: 検索開始日
    :return:
    """
    result = [
        {
            'reservation_id': 'R000000001',
            'device_id': device_id,
            'device_name': 'DUMMY DEVICE NAME',
            'start_time': '20210625143000000000',
            'end_time': '20210625150000000000',
            'reserver_id': 'PERSON0001',
            'reserver_name': '建機　花子',
        },
        {
            'reservation_id': 'R000000002',
            'device_id': device_id,
            'device_name': 'DUMMY DEVICE NAME',
            'start_time': '20210625153000000000',
            'end_time': '20210625163000000000',
            'reserver_id': 'PERSON0002',
            'reserver_name': '重機　太郎',
        },
    ]
    return result
