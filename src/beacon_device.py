import time

from beacontools import BeaconScanner, IBeaconFilter, IBeaconAdvertisement


def callback(bt_addr, rssi, packet:IBeaconAdvertisement, properties):
    """
    Beacon callback　デバイスに実装
    :param bt_addr: e2:ac:43:37:a0:58,
    :param rssi: -52,
    :param packet: IBeaconAdvertisement<tx_power: 0, uuid: 01234567-8901-2345-6789-012345678901, major: 0, minor: 0>
    :param properties: {'uuid': '01234567-8901-2345-6789-012345678901', 'major': 0, 'minor': 0}
    :return:
    """
    tx_power = packet.tx_power
    distance = pow(10.0, (tx_power - rssi) / 20.0)
    print(f'distance:{distance}, rssi:{rssi}, tx_power:{tx_power}')


if __name__ == '__main__':
    # scan for all iBeacon advertisements from beacons with certain properties:
    # - uuid
    # - major
    # - minor
    # at least one must be specified.
    scanner = BeaconScanner(
        callback,
        device_filter=IBeaconFilter(major=0),
        # device_filter=IBeaconFilter(uuid="01234567-8901-2345-6789-012345678901"),
        )
    scanner.start()
    while True:
        time.sleep(1)

    scanner.stop()
