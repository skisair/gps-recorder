from flask import Flask
from flask import request, make_response, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder="./build/static", template_folder="./build")
CORS(app) #Cross Origin Resource Sharing

@app.route("/", methods=['GET'])
def index():
    return "text parser:)"

# API
'''
・機械一覧の取得
    ・機械ID
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
・機械履歴取得
    ・機械ID
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