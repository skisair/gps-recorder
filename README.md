# gps-recorder

## 起動方法
MQTT/Azurite/Data Analyzerの起動
```bash
docker compose up 
```
バックグラウンドサービスとして起動・停止する場合
```bash
docker compose up -d
docker compose down
```

その他のサービスの起動
```
pip install -r requiremnts.txt

source config/gps_device.env
python src/gps_device.py

source config/camera_device.env
python src/camera_device.py
```

## Docker構成
- UI（Flask）
- MQTT
- データ格納/デバイス制御
- Azurite(データベース)
- GPS・カメラデバイス

WindowsではDockerにUSBをマウントするのが手間なので、ViewerとMQTTのみDockerが良さそう。

データ格納・デバイス制御はAzure IoT Hubへ、データベースはAzure Table Storageへ移行することを前提とする。

## デバイス側プロセス
- 自身のデバイスIDを取得
- データレイアウトをロード
- 各種センサーから情報を取得
- データをJSON形式に変換
- 内部時計のタイムスタンプ・メッセージID・デバイスIDを付与
- MQTTにデータトピックでPublish
- データをJson形式でフォルダに出力

※デバイスIDは今回は環境変数として付与する。

環境変数
- GPS_PORT　必須：Macでは/dev/tty.usbmodem14101など、WindowsではCOM3,COM4など
- DEVICE_ID デフォルトでマシン名取得
- OUTPUT_FOLDER デフォルトで、data/${device_id}
- OUTPUT_FOLDER_FORMAT デフォルトで、%Y/%m/%d/%H
- OUTPUT_FILE_FORMAT　デフォルトで、%Y%m%d%H%M%S%f-${data_id}-${id}.json
- MQTT_HOST デフォルトで、localhost
- MQTT_PORT デフォルトで、1883
- MQTT_KEEP_ALIVE デフォルトで60秒
- MQTT_TOPIC デフォルトで'gps/sensor_data'
- LOG_LEVEL デフォルトでINFO


## データ格納プロセス
- MQTTにデータトピックでSubscribe
- 受信したメッセージをデータベースに格納
- データをJson形式でフォルダに出力
- MQTTにデータ更新トピックでPublish（指定間隔）
- 指定アルゴリズムで、データを解析・新たなデータ種別として格納

- OUTPUT_FOLDER デフォルトで、data/${device_id}
- OUTPUT_FOLDER_FORMAT デフォルトで、%Y/%m/%d/%H
- OUTPUT_FILE_FORMAT　デフォルトで、%Y%m%d%H%M%S%f-${data_id}-${id}.json

※データ解析は後日実装

## UI（Flask）
- データ更新トピックをSubscribe
- データ更新トピックの内容を保存
- SocketIOによってブラウザとサーバで通信
- デバイスID/デバイス名一覧の返却
- データ種別ID/データ種別名の返却
- デバイスID・時刻・データ種別でデータを検索
- データ更新があった際には差分データを返却

## UI(ブラウザ)
- デバイス一覧、データ種別一覧から閲覧データを選択
- Plotlyでグラフ描画
- パラパラ漫画で動画を描画
※まずは固定で実装

## テーブル構成
- デバイスマスタ mdevice
  - PK: デバイスID device_id
  - RK: データ種別ID data_id
  - デバイス名 device_name

- データ種別マスタ mdata
  - PK: データ種別ID data_id
  - RK: 項目ID item_id 
  - 項目名 item_name
  - Max値 value_max
  - Min値 value_min
  
- データトラン tdata
  - PK: デバイスID-データ種別
  - RK: タイムスタンプ

※画像は、サイズによって検討一旦テーブル内格納を検討

## GPSデータ構造（NMEAフォーマット）
### $GPRMC

$GPRMC,013728.00,A,3537.51961,N,13941.60464,E,0.140,,190621,,,A*71

| item_id | item_name | sample | |
| --- | --- | --- | --- |
| data_id | データ種別ID | $GPRMC | |
| utc_time | UTC時刻(%H%M%S.%f') | 013728.00 | 01:37:28.00 |
| warning | ステータス | A | A = OK, V = warning |
| lat | 緯度 | 3537.51961 | 35 deg 37.51961 min |
| lat_d| 北緯・南緯 | N | North |
| lng | 経度 | 13945.3994 | 139 deg 45.3994 min |
| lng_d | 東経・西経 | E | East |
| speed | 移動速度 | 000.0 | knot |
| course | 移動の方向 | 240.3 | |
| utc_date | UTC日付(%d%m%y) | 190621 | 2021/06/19 |
| variation | 磁北との差角度 | | 0~360 |
| variation_d| 磁北との差方向| | E:東 / W:西 |
| mode | モード | A | |
| check_sum | チェックサム | 6A | |

### $GPGGA

$GPGGA,013728.00,3537.51961,N,13941.60464,E,1,07,1.39,28.1,M,39.3,M,,*6B

| item_id | item_name | sample | |
| --- | --- | --- | --- |
| data_id | データ種別ID | $GPGGA | |
| utc_time | UTC時刻 | 013728.00 | 01:37:28.00 |
| lat | 緯度 | 3537.51961 | 35 deg 37.51961 min |
| lat_d| 北緯・南緯 | N | |
| lng | 経度 | 13941.60464 | |
| lng_d | | E | |
| fix_quality | 位置特定品質 | 1 | 0 = Invalid、1 = GPS fix、2 = DGPS fix |
| num_satellites | 使用衛星数 | 07 |  |
| hdop | 水平精度低下率 | 1.39 | Horizontal Dilution of Precision (HDOP) |
| altitude | アンテナの海抜高さ | 28.1 |  |
| alt_m | メートル | M |  |
| geoid_height | ジオイド高さ	 | 39.3 |  |
| geo_m | メートル | M |  |
| dgps_update | DGPSデータの最後の有効なRTCM通信からの時間 |  |  |
| dgps_id | 差動基準地点ID |  |  |
| check_sum | チェックサム | 5E | |


### $GPVTG

$GPVTG,240.3,T,,M,000.0,N,000.0,K,A*08

| item_id | item_name | sample | |
| --- | --- | --- | --- |
| data_id | データ種別ID | $GPVTG | |
| course | 移動の方向 | 240.3 | 240.3 deg |
| true_course |  | T | - |
| m_course |  |  |  |
| mag_course |  | M | - |
| k_speed | 移動速度(Knot) | 000.0 | 000.0 knot |
| speed_k_unit | 単位(Knot) | N | knot |
| m_speed | 移動速度(Km) | 000.0 | 000.0 km/h |
| speed_m_unit | 単位(Km/h) | K | kiro |
| mode |  | A | A:Autonomous / D:Differential / E:Estimated |
| check_sum |  | 08 |  |


### $GPGSA

$GPGSA,A,3,16,07,01,27,21,10,08,,,,,,2.24,1.39,1.76*03

| item_id | item_name | sample | |
| --- | --- | --- | --- |
| data_id | データ種別ID | $GPGSA | |
| mode | モード | A | A:Auto/M:Manual | 
| type | 特定方式 | 3 | 1:No / 2:2D / 3:3D | 
| satellite_01 | 衛星01 | 16 |  |
| satellite_02 | 衛星02 | 07 |  |
| satellite_03 | 衛星03 | 01 |  |
| satellite_04 | 衛星04 | 27 |  |
| satellite_05 | 衛星05 | 21 |  |
| satellite_06 | 衛星06 | 10 |  |
| satellite_07 | 衛星07 | 08 |  |
| satellite_08 | 衛星08 |  |  |
| satellite_09 | 衛星09 |  |  |
| satellite_10 | 衛星10 |  |  |
| satellite_11 | 衛星11 |  |  |
| satellite_12 | 衛星12 |  |  |
| pdop | 位置精度低下率 | 2.24 |  |
| hdop | 水平精度低下率 | 1.39 |  |
| vdop | 垂直精度低下率 | 1.76 |  |
| check_sum |  | 03 |  |


### $GPGSV

$GPGSV,4,1,13,01,61,223,21,03,10,173,12,07,38,245,21,08,56,042,33*7D

$GPGSV,4,2,13,10,14,045,36,14,15,314,17,16,16,130,24,17,02,272,*7B

$GPGSV,4,3,13,21,88,312,15,22,30,155,21,27,28,071,36,28,01,313,*7C

$GPGSV,4,4,13,30,29,291,18*40


| item_id | item_name | sample | |
| --- | --- | --- | --- |
| data_id | データ種別ID | $GPGSV | |
| total_messages | 総メッセージ数 | 4 | |
| message_number | メッセージ番号 | 1 | |
| total_sv | ビュー内の総衛星数 | 13 |  |
| sv_prn | 衛星番号 | 01 |  | 
| el_degree | 仰角 | 61 |  |
| az_degree | 北からの角度 | 223 |  |
| srn | キャリア／ノイズ比(dB) | 21 |
| sv_prn | 衛星番号 | 03 |  | 
| el_degree | 仰角 | 10 |  |
| az_degree | 北からの角度 | 173 |  |
| srn | キャリア／ノイズ比(dB) | 12 |
| sv_prn | 衛星番号 | 07 |  | 
| el_degree | 仰角 | 38 |  |
| az_degree | 北からの角度 | 245 |  |
| srn | キャリア／ノイズ比(dB) | 21 |
| sv_prn | 衛星番号 | 08 |  | 
| el_degree | 仰角 | 56 |  |
| az_degree | 北からの角度 | 042 |  |
| srn | キャリア／ノイズ比(dB) | 33 |
| check_sum |  | 7D |  |

### $GPGLL

$GPGLL,3537.51961,N,13941.60464,E,013728.00,A,A*60


| item_id | item_name | sample | |
| --- | --- | --- | --- |
| data_id | データ種別ID | $GPGLL | |
| lat | 緯度 | 3537.51961 | 35 deg 37.51961 min |
| lat_d| 北緯・南緯 | N | North |
| lng | 経度 | 13941.60464 | 139 deg 41.60464 min |
| lng_d | 東経・西経 | E | East |
| utc_time |  | 013728.00 | 01:37:28.00UTC |
| warning | ステータス | A | A:OK / V:warning |
| mode | 測位モード | A |　N:None / A:Single / D:DGPS  |
| check_sum |  | 60 |  |


参考元URL
- https://www.hiramine.com/physicalcomputing/general/gps_nmeaformat.html
- http://www.spa-japan.co.jp/tech/Tech103_UbloxNmea.html
- http://aprs.gids.nl/nmea/