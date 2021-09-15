import os
import threading

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, send, join_room, leave_room

from web_serial_controller import SerialController, DummySerialController

SERIAL_PORT = os.environ.get('SERIAL_PORT', default='/dev/serial0')
BAUD_RATE = int(os.environ.get('BAUD_RATE', default='9600'))
SIGNAL_INTERVAL = int(os.environ.get('SIGNAL_INTERVAL', default='10'))
SIGNAL_INTERVAL = int(os.environ.get('SIGNAL_INTERVAL', default='10'))

app = Flask(__name__)
socketio = SocketIO(app)


@socketio.on('control')
def control(message):
    app.logger.info(message)
    serial_controller.set_signal(message)
    emit('status', message, broadcast=True)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == "__main__":
    print('start up')
    try:
        serial_controller = SerialController(port=SERIAL_PORT, baud_rate=BAUD_RATE)
    except Exception as e:
        serial_controller = DummySerialController(port=SERIAL_PORT, baud_rate=BAUD_RATE)

    thread = threading.Thread(target=serial_controller.run)
    thread.daemon = True
    thread.start()

    app.debug = True
    socketio.run(app, host='0.0.0.0', port=8081, use_reloader=False)

