#! /usr/local/bin/python3.6
"""
BLH -> ECEF 変換
: WGS84 の緯度(Beta)／経度(Lambda)／楕円体高(Height)を
  ECEF（Earth Centered Earth Fixed; 地球中心・地球固定直交座標系）座標に
  変換する。

  Date          Author          Version
  2018.06.28    mk-mode.com     1.00 新規作成

Copyright(C) 2018 mk-mode.com All Rights Reserved.
---
引数: LATITUDE(BETA) LONGITUDE(LAMBDA) HEIGHT
"""
import math
import sys
import traceback


class BlhToEcef:
    USAGE = "[USAGE] ./blh2ecef.py LATITUDE(BETA) LONGITUDE(LAMBDA) HEIGHT"
    PI_180 = math.pi / 180.0
    # WGS84 座標パラメータ
    A      = 6378137.0                # a(地球楕円体長半径(赤道面平均半径))
    ONE_F  = 298.257223563            # 1 / f(地球楕円体扁平率=(a - b) / a)
    B      = A * (1.0 - 1.0 / ONE_F)  # b(地球楕円体短半径)
    E2     = (1.0 / ONE_F) * (2 - (1.0 / ONE_F))
    # e^2 = 2 * f - f * f
    #     = (a^2 - b^2) / a^2
    ED2    = E2 * A * A / (B * B)     # e'^2= (a^2 - b^2) / b^2

    def __init__(self):
        """ Initialization
            : コマンドライン引数の取得
        """
        try:
            if len(sys.argv) < 4:
                print(self.USAGE)
                sys.exit(0)
            self.lat, self.lon, self.ht = \
                map(lambda x: float(x), sys.argv[1:4])
        except Exception as e:
            raise

    def exec(self):
        """ Execution """
        try:
            print((
                      "BLH: LATITUDE(BETA) = {:12.8f}°\n"
                      "  LONGITUDE(LAMBDA) = {:12.8f}°\n"
                      "             HEIGHT = {:7.3f}m"
                  ).format(self.lat, self.lon, self.ht))
            x, y, z = self.__blh2ecef(self.lat, self.lon, self.ht)
            print("--->")
            print((
                      "ECEF: X = {:12.3f}m\n"
                      "      Y = {:12.3f}m\n"
                      "      Z = {:12.3f}m"
                  ).format(x, y, z))
        except Exception as e:
            raise

    def __blh2ecef(self, lat, lon, ht):
        """ BLH -> ECEF 変換

        :param  float lat: Latitude
        :param  float lon: Longitude
        :param  float  ht: Height
        :return list ecef: ECEF Coordinate [x, y, z]
        """
        try:
            n = lambda x: self.A / \
                          math.sqrt(1.0 - self.E2 * math.sin(x * self.PI_180)**2)
            x = (n(lat) + ht) \
                * math.cos(lat * self.PI_180) \
                * math.cos(lon * self.PI_180)
            y = (n(lat) + ht) \
                * math.cos(lat * self.PI_180) \
                * math.sin(lon * self.PI_180)
            z = (n(lat) * (1.0 - self.E2) + ht) \
                * math.sin(lat * self.PI_180)
            return [x, y, z]
        except Exception as e:
            raise


if __name__ == '__main__':
    try:
        obj = BlhToEcef()
        obj.exec()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)