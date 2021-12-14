import asyncio
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from web_serial_controller import SerialController, DummySerialController

SERIAL_PORT = os.environ.get('SERIAL_PORT', default='/dev/serial0')
BAUD_RATE = int(os.environ.get('BAUD_RATE', default='9600'))
SIGNAL_INTERVAL = int(os.environ.get('SIGNAL_INTERVAL', default='10'))
SIGNAL_INTERVAL = int(os.environ.get('SIGNAL_INTERVAL', default='10'))

app = Flask(__name__)
socketio = SocketIO(app)

@socketio.on('signal', namespace='/web-ctl')
def control(message):
    app.logger.info(message)
    emit('signal', message, broadcast=True, namespace='/web-ctl')

@socketio.on('control', namespace='/web-ctl')
def control(message):
    app.logger.info(message)
    serial_controller.set_signal(message)
    emit('status', message, broadcast=True, namespace='/web-ctl')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == "__main__":
    print('start up')
    loop = asyncio.get_event_loop()
    try:
        serial_controller = SerialController.get_instance(port=SERIAL_PORT, baud_rate=BAUD_RATE, loop=loop)
    except Exception as e:
        serial_controller = DummySerialController.get_instance(port=SERIAL_PORT, baud_rate=BAUD_RATE, loop=loop)

    app.debug = True
    socketio.run(app, host='0.0.0.0', port=8081, use_reloader=False)

