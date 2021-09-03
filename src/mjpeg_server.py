#!/usr/bin/python
import io

import cv2
from PIL import Image
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import time
import threading

capture = None
len_view = 0
view = []

CV_CAP_PROP_FRAME_WIDTH = 3
CV_CAP_PROP_FRAME_HEIGHT = 4
CV_CAP_PROP_SATURATION = 12

WIDTH = 320
HEIGHT = 240

VIEW_RATE = 1

INTERVAL = 0.1


class CamHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        global view
        global len_view
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jb')
            self.end_headers()
            boundary = '--jb'.encode()
            while True:
                try:
                    self.wfile.write(boundary)
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', len_view)
                    self.end_headers()
                    self.wfile.write(view)
                    self.wfile.flush()
                    time.sleep(INTERVAL)
                except ConnectionAbortedError:
                    break
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write('<html><head>'.encode())
            self.wfile.write('<style type="text/css">'.encode())
            self.wfile.write('p { font-size: 12ex; }'.encode())
            self.wfile.write('</style>'.encode())
            self.wfile.write('</head><body>'.encode())
            self.wfile.write('<p id="RealtimeClockArea"></p><br>'.encode())
            self.wfile.write(f'<img src="./cam.mjpg" height="{HEIGHT * VIEW_RATE}" width="{WIDTH * VIEW_RATE}"/><br>'.encode())

            script = (
                'function zeroPadding(NUM, LEN){\n'
                '   return ( Array(LEN).join(\'0\') + NUM ).slice( -LEN );\n'
                '}\n'
                'function showClock2() {\n'
                '   var nowTime = new Date();\n'
                '   var nowSec  = zeroPadding(nowTime.getSeconds(), 2);\n'
                '   var nowMiliSec = zeroPadding(nowTime.getMilliseconds(), 3);\n'
                '   var msg = nowSec + "." + nowMiliSec;\n'
                '   document.getElementById("RealtimeClockArea").innerHTML = msg;\n'
                '}'
                'setInterval(\'showClock2()\',100);'
            )

            self.wfile.write(f'<script>\n{script}</script>\n'.encode())
            self.wfile.write('</body></html>'.encode())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass


def thread_task(lock):
    global view
    global len_view
    while True:
        try:
            rc, img = capture.read()
            if not rc:
                continue
            img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
            # img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            jpg = Image.fromarray(img)
            buffer = io.BytesIO()
            jpg.save(buffer, 'JPEG', quality=10, optimize=True)
            tmp_view = buffer.getbuffer()
            view = tmp_view
            len_view = len(view)
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
                break


def main():
    global capture

    capture = cv2.VideoCapture(0)
    capture.set(CV_CAP_PROP_FRAME_WIDTH, WIDTH)
    capture.set(CV_CAP_PROP_FRAME_HEIGHT, HEIGHT)
    # capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    capture.set(CV_CAP_PROP_SATURATION, 64)

    lock = threading.Lock()
    t1 = threading.Thread(target=thread_task, args=(lock,))
    t1.start()
    try:
        server = ThreadedHTTPServer(('0.0.0.0', 8080), CamHandler)
        print("server started")
        server.serve_forever()
    except KeyboardInterrupt:
        capture.release()
        server.socket.close()
    t1.join()


if __name__ == '__main__':
    main()