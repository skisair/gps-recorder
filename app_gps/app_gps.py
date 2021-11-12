import math

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import os
import logging
import platform
import threading
from datetime import timezone, timedelta
from gps_device import GpsDevice
from util.exporter import QueueExporter, queue_list

GPS_PORT = os.environ.get('GPS_PORT', default='/dev/tty.usbmodem14101')
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

def radar_chart(datas):
    print('----------------------------')
    xs = []
    ys = []
    srns = []
    keys = []
    for key, value in datas.items():
        print(f'{key}: {value}')
        # el_degree: 仰角（0~90）水平が0 / 天井が90
        # az_degree: 方位角度(0~360) 北が0 / 東が90
        # srn: 00～99dB
        el_degree = 90 - value['el_degree']
        az_degree = 360 - value['az_degree'] + 90
        srn = value['srn']
        x = math.cos(az_degree * math.pi / 180) * el_degree
        y = math.sin(az_degree * math.pi / 180) * el_degree
        keys.append(key)
        xs.append(x)
        ys.append(y)
        srns.append(srn)

    layout = go.Layout(
        autosize=False,
        xaxis=dict(range=[-90,90], dtick=30),
        yaxis=dict(range=[-90,90], dtick=30, scaleanchor='x', scaleratio=1.0))

    fig = go.Figure(data=go.Scatter(
        x=xs,
        y=ys,
        text=keys,
        mode='markers+text',
        marker=dict(size=srns)
        ), layout=layout)
    fig.update_layout(
        height=600, width=600,
    )
    #fig.update_layout(scaleratio=1.0)
    placeholder_place.write(fig, )
    fig2 = go.Figure(data=go.Bar(
        x=keys,
        y=srns,
    ))
    #fig2 = px.bar(df_mean, x='month', y='スノーピーク')
    placeholder_srn.write(fig2,)

# ------------------------

device_id = DEVICE_ID
device = None
device = GpsDevice(device_id, GPS_PORT, dummy_script=DUMMY_SCRIPT)
queue_exporter = QueueExporter(device_id)
device.add(queue_exporter)
queue = queue_list[device_id]
thread = threading.Thread(target=device.run)

try:
    thread.start()
    datas = {}
    while True:
        message = queue.get()
        if message['data_id'] == 'GPGSV':
            sv_num = message['sv_num']
            if sv_num == 1:
                radar_chart(datas)
                datas = {}
            sv_prn = message['sv_prn']
            datas[f'G{sv_prn:0>2}'] = {
                'el_degree': message['el_degree'],
                'az_degree': message['az_degree'],
                'srn': message['srn'],
            }
except KeyboardInterrupt as e:
    device.stop()
    thread.join()