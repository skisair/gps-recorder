from datetime import datetime, timedelta, timezone

from flask import Flask
from flask import request, make_response, jsonify
from flask_cors import CORS

import dao

JST = timezone(timedelta(hours=+9), 'JST')

app = Flask(__name__, static_folder="./build/static", template_folder="./build")
# 別プロセスからの応答を返却するために必要
CORS(app)

@app.route('/list_device', method=['GET','POST'])
def list_device():
    """
    機械一覧の取得（配列）
    ・機械ID
    ・機械名
    ・最終通信時刻
    ・緯度/経度
    ・直近予約状況（N件）
        ・予約ID
        ・予約時間
        ・予約者ID
        ・予約者名
    ・最終近接駐機場
        ・駐機場ID
        ・駐機場名
    ・状態
    ・最終乗車者
    :return:
    """
    input_parameter = request.get_json()
    response = dao.list_device()
    for device in response:
        device_id = device['device_id']
        # 現在より30前スタートの予約情報を返却
        from_time = datetime.now(JST) - timedelta(minutes=30)
        reservations = dao.list_reservation(device_id=device_id, from_time=from_time)
        device['reservations'] = []
        for reservation in reservations:
            del reservation['device_id']
            del reservation['device_name']
            device['reservations'].append(reservation)

    return make_response(jsonify(response))



@app.route('/get_device', method=['GET','POST'])
def get_device():
    input_parameter = request.get_json()
    device_id = input_parameter['device_id']
    response = dao.get_device(device_id)
    return make_response(jsonify(response))


# API
'''
・機械履歴取得
    ・機械ID
    ・機械名
    ・位置情報履歴
        ・時刻
        ・位置情報
    ・駐機場履歴
        ・時刻
        ・駐機場ID
        ・距離？
    ・乗車履歴
        ・予約者ID
        ・乗車時刻
        ・返却時刻
・駐車場情報の取得
    ・駐車場ID
    ・駐車場名
    ・駐機機械一覧
        ・機械ID
・予約一覧の取得（日付）
    ・予約ID
    ・予約者ID
    ・予約者名
    ・予約時間
    ・機械ID
・予約状況取得（機械ID）
    ・予約ID
    ・予約者ID
    ・予約者名
    ・予約時刻
・予約
    ・予約者ID
    ・予約時間
    ・機械ID
・予約キャンセル
    ・予約ID
・乗車
    ・予約者ID
    ・機械ID
    （予約中・直近予約が入っていれば返却）
・返却
    ・予約者ID
    ・機械ID

'''

@app.route("/wakati", methods=['GET','POST'])
def parse():
    #print(request.get_json()) # -> {'post_text': 'テストテストテスト'}
    data = request.get_json()
    text = data['post_text']
    res = text.split(',')
    response = {'result': res}
    #print(response)
    return make_response(jsonify(response))


if __name__ == "__main__":
    app.debug = True
    app.run(host='127.0.0.1', port=5000)