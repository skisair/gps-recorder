import os
import logging
import platform
import threading
import math
import queue
from datetime import datetime, timezone, timedelta

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from gps_device import GpsDevice
from util.exporter import QueueExporter, queue_list

# https://github.com/commaai/laika
# https://nyanchew.com/?q=jp/%E3%82%A2%E3%83%AB%E3%83%9E%E3%83%8A%E3%83%83%E3%82%AF%E3%81%8B%E3%82%89gps%E8%A1%9B%E6%98%9F%E3%81%AE%E4%BD%8D%E7%BD%AE%E3%82%92%E6%B1%82%E3%82%81%E3%82%8B%E6%96%B9%E6%B3%95
# https://sys.qzss.go.jp/dod/api.html
# https://sys.qzss.go.jp/dod/api/search/ephemeris-qzss?since_datetime=2021-11-13%2000:00:00&until_datetime=2021-11-14%2000:00:00
# https://sys.qzss.go.jp/dod/api/get/ephemeris-qzss?id=brdc3160.21n
# https://sys.qzss.go.jp/dod/api/get/ephemeris-qzss?id=brdc3160.21q

GPS_PORT = os.environ.get('GPS_PORT', default='/dev/tty.usbserial-1410')
DEVICE_ID = os.environ.get('DEVICE_ID', default=platform.uname()[1])
LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)
DUMMY_SCRIPT = os.environ.get('DUMMY_SCRIPT', default='')  # dummy/gps/gps-sample001.txt

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)

placeholder_place = st.empty()
placeholder_srn = st.empty()


def draw(datas):
    keys = list(datas.keys())
    srns = []
    srn_max = []
    azimuths_radians = []
    elevation_radians = []
    xs = []
    ys = []

    xc90 = []
    yc90 = []
    xc60 = []
    yc60 = []
    xc30 = []
    yc30 = []
    for angle in range(0, 361, 10):
        x = math.cos(angle * math.pi / 180)
        y = math.sin(angle * math.pi / 180)
        xc90.append(x*90)
        yc90.append(y*90)
        xc60.append(x*60)
        yc60.append(y*60)
        xc30.append(x*30)
        yc30.append(y*30)

    for key in datas.keys():
        #print(f'{key}:{value}')
        # el_degree: 仰角（0~90）水平が0 / 天井が90
        # az_degree: 方位角度(0~360) 北が0 / 東が90
        # srn: 00～99dB
        value = datas[key]
        el_degree = 90 - value['el_degree']
        az_degree = 360 - value['az_degree'] + 90
        azimuths_radians.append(az_degree * math.pi / 180)
        elevation_radians.append(el_degree * math.pi / 180)
        srn = value['srn']
        x = math.cos(az_degree * math.pi / 180) * el_degree
        y = math.sin(az_degree * math.pi / 180) * el_degree
        xs.append(x)
        ys.append(y)
        srns.append(srn)
        srn_max.append(stats[key]['srn_max'])

    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'polar'}, {'type':'xy'}]])

    fig.add_traces(
        data=[go.Scatterpolar(
            theta=np.array(azimuths_radians)*180/np.pi,
            r=np.array(elevation_radians)*180/np.pi,
            mode='markers',
            marker=dict(size=np.array(srns) + 10),
            text=keys,
            textposition='top center',
        ),
        go.Bar(
            x=keys,
            y=srn,
            xaxis='x1',
            yaxis='y1'
        ),
        go.Bar(
            x=keys,
            y=srn_max,
            xaxis='x1',
            yaxis='y1'
        )],
        rows=[1,1,1],
        cols=[1,2,2],
    )
    fig.update_layout(
        dict(
            polar=dict(
                angularaxis=dict(
                    direction='clockwise',
                ),
            ),
            #xaxis=dict(range=[-90,90], dtick=30),
            #yaxis=dict(range=[-90,90], dtick=30, scaleanchor='x', scaleratio=1.0),
            xaxis=dict(),
            yaxis=dict(range=[0, 100], dtick=20),
            showlegend=False,
        )
    )

    placeholder_place.write(fig, )

# ------------------------
@st.experimental_singleton
def get_queue():
    device_id = DEVICE_ID
    device = GpsDevice(device_id, GPS_PORT, dummy_script=DUMMY_SCRIPT)
    mem_queue = queue.Queue()
    queue_exporter = QueueExporter(device_id, mem_queue)
    device.add(queue_exporter)
    thread = threading.Thread(target=device.run)
    thread.start()
    return mem_queue

try:
    stats = {}
    last_update = datetime.now(JST)
    mem_queue = get_queue()
    while True:
        message = mem_queue.get()
        data_id = message['data_id']
        if (data_id == 'GPGSV') or (data_id == 'GNGSV'):
            # logger.info(message)
            sv_num = message['sv_num']
            sv_prn = message['sv_prn']
            sv_prn = f'G{sv_prn:0>2}'

            if sv_prn not in stats:
                stats[sv_prn] = {}
                stats[sv_prn]['srn_max'] = message['srn']
            elif stats[sv_prn]['srn_max'] < message['srn']:
                stats[sv_prn]['srn_max'] = message['srn']

            stats[sv_prn]['el_degree'] = message['el_degree']
            stats[sv_prn]['az_degree'] = message['az_degree']
            stats[sv_prn]['srn'] = message['srn']
            stats[sv_prn]['last_update'] = datetime.now(JST)

        if (last_update + timedelta(seconds=5)) < datetime.now(JST):
            for sv_prn, value in stats.items():
                if value['last_update'] < last_update:
                    value['srn'] = 0
                logger.info(f'{sv_prn}:{value}')
            draw(stats)
            last_update = datetime.now(JST)

except KeyboardInterrupt as e:
    pass