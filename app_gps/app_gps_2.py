import os
import logging
from datetime import datetime, timezone, timedelta
import platform
import threading
import re
import requests
import queue

import folium
from streamlit_folium import folium_static
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ephem
from gps_device import GpsDevice
from util.exporter import QueueExporter
import pandas as pd


GPS_PORT = os.environ.get('GPS_PORT', default='/dev/tty.usbmodem14101')
DEVICE_ID = os.environ.get('DEVICE_ID', default=platform.uname()[1])
LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)
DUMMY_SCRIPT = os.environ.get('DUMMY_SCRIPT', default='')  # dummy/gps/gps-sample001.txt

JST = timezone(timedelta(hours=+9), 'JST')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)

# ------------------------------------------------------------------------------------
st.markdown("# GNSS Satellite Viewer")
placeholder_place = st.empty()
placeholder_df = st.empty()
placeholder_map = st.empty()

st.session_state['lat'] = st.sidebar.text_input(
    f"lat:",
    value='35.685237',
)
st.session_state['lon'] = st.sidebar.text_input(
    f"lon:",
    value='139.4167183',
)

observer = ephem.Observer()
observer.lat = st.session_state['lat']
observer.lon = st.session_state['lon']
observer.elevation = 0.0

m = folium.Map(location=[st.session_state['lat'], st.session_state['lon']])
marker = folium.Marker(
    location=[st.session_state['lat'], st.session_state['lon']],
    popup=f'{observer.lat},{observer.lon}'
).add_to(m)

with placeholder_map:
    folium_static(m)

def update(datas):

    # 35.685237,139.4167183
    observer.date = datetime.utcnow()
    orbits = {}
    for gnss_name, satellite in gnss_list.items():
        satellite.compute(observer)
        if satellite.alt > 0:
            if gnss_name not in datas:
                datas[gnss_name] = {
                    'sv_prn': gnss_name,
                    'srn': 0,
                    'srn_max': 0,
                    'el_degree': satellite.alt * 180 / np.pi,
                    'az_degree': satellite.az * 180 / np.pi,
                    'last_update': datetime.now(JST)
                }
            datas[gnss_name]['el_degree_n'] = satellite.alt * 180 / np.pi
            datas[gnss_name]['az_degree_n'] = satellite.az * 180 / np.pi

            observer_tmp = observer.copy()
            el_degrees = []
            az_degrees = []
            rising = True
            setting = True
            interval=15
            hours = 6
            el_degrees.append(datas[gnss_name]['el_degree_n'])
            az_degrees.append(datas[gnss_name]['az_degree_n'])
            for i in range(int(interval/2), hours*60, 15):

                observer_tmp.date = datetime.utcnow() - timedelta(minutes=i)
                satellite.compute(observer_tmp)
                if rising and (satellite.alt >= 0):
                    el_degrees.insert(0, satellite.alt * 180 / np.pi)
                    az_degrees.insert(0, satellite.az * 180 / np.pi)
                else:
                    rising = False

                observer_tmp.date = datetime.utcnow() + timedelta(minutes=i)
                satellite.compute(observer_tmp)
                if setting or (satellite.alt >= 0):
                    el_degrees.append(satellite.alt * 180 / np.pi)
                    az_degrees.append(satellite.az * 180 / np.pi)
                else:
                    setting = False

                if (rising == False) and (setting == False):
                    break

            orbits[gnss_name] = {
                'el_degrees': el_degrees,
                'az_degrees': az_degrees,
            }


    df = pd.DataFrame(list(datas.values()))
    placeholder_df.dataframe(df[['sv_prn', 'srn', 'srn_max', 'el_degree', 'el_degree_n', 'az_degree', 'az_degree_n', 'last_update']],)

    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'polar'}, {'type':'xy'}]])

    layout = go.Layout(
        polar=dict(
            angularaxis=dict(
                direction='clockwise',
            ),
            radialaxis=dict(
                range=[0,90],
                showticklabels=False,
            )
        ),
        autosize=False,
        xaxis1=dict(),
        yaxis1=dict(range=[0, 100], dtick=20),
        showlegend=False,
    )
    fig.add_traces(
        # 衛星位置
        data=[
            go.Scatterpolar(
                theta=df['az_degree'],
                r=90.0 - df['el_degree'],
                mode='markers+text',
                marker=dict(
                    color='blue',
                    opacity=0.5,
                    size=np.array(df['srn'])
                ),
                text=df['sv_prn'],
                textposition='top center',
            ),
            go.Scatterpolar(
                theta=df['az_degree'],
                r=90.0 - df['el_degree'],
                mode='markers',
                marker=dict(
                    color='red',
                    opacity=0.5,
                    symbol=4,
                ),
                text=df['sv_prn'],
                textposition='top center',
            ),
        ],
        rows=[1, 1],
        cols=[1, 1],
    )
    for gnss_name, orbit in orbits.items():
        # print(orbit)
        fig.add_trace(
            trace=go.Scatterpolar(
                theta=np.array(orbit['az_degrees']),
                r=90.0 - np.array(orbit['el_degrees']),
                mode='lines',
                line=dict(
                    color='red',
                ),
                text=gnss_name,
                opacity=0.1,
                hoverinfo='skip',
            ),
            row=1,
            col=1,
        )
    fig.add_traces(
        data=[
            go.Bar(
                x=df['sv_prn'],
                y=df['srn'],
                xaxis='x1',
                yaxis='y1',
                marker=dict(
                    color='blue',
                    opacity=0.5,
                )
            ),
            go.Bar(
                x=df['sv_prn'],
                y=df['srn_max'],
                xaxis='x1',
                yaxis='y1',
                marker=dict(
                    color='red',
                    opacity=0.5,
                )
            ),
        ],
        rows=[1, 1],
        cols=[2, 2],
    )
    fig.update_layout(
        layout,
    )
    placeholder_place.write(fig, )



@st.experimental_singleton
def start():
    device_id = DEVICE_ID
    device = GpsDevice(device_id, GPS_PORT, dummy_script=DUMMY_SCRIPT)
    mem_queue = queue.Queue()
    queue_exporter = QueueExporter(device_id, mem_queue)
    device.add(queue_exporter)
    thread = threading.Thread(target=device.run)
    thread.start()
    return mem_queue


@st.experimental_singleton
def get_gnss_list():
    gnss_resp = requests.get('https://www.celestrak.com/NORAD/elements/gnss.txt')
    lines = gnss_resp.text.split('\r\n')
    gnss_list = {}
    for i in range(0, len(lines), 3):
        satellite_desc = lines[i]
        if satellite_desc.find('GPS') >= 0:
            res = re.match(r'.*?PRN (.*?)\).*?', satellite_desc)
            id = res.group(1)
            gnss_name = f'G{id}'
            satellite = ephem.readtle(gnss_name, lines[i + 1], lines[i + 2])
            gnss_list[gnss_name] = satellite
    return gnss_list


last_update = datetime.now(JST)

try:
    mem_queue = start()
    gnss_list = get_gnss_list()
    datas = {}

    while True:
        message = mem_queue.get()
        # print(message)
        now = datetime.now(JST)
        if message['data_id'][-3:] == 'GGA':
            observer.elevation = message['altitude'] + message['geoid_height']
            st.session_state['lat'] = str(message['lat'])
            st.session_state['lon'] = str(message['lon'])
            observer.lat = str(message['lat'])
            observer.lon = str(message['lon'])

            #del m.template_vars.get('custom_markers')[0]
            #folium.Marker(
            #    location=[st.session_state['lat'], st.session_state['lon']],
            #    popup=f'{observer.lat},{observer.lon}'
            #).add_to(m)


        if message['data_id'][-3:] == 'GSV':
            sv_prn = message['sv_prn']
            sv_prn = f'G{sv_prn}'
            if sv_prn not in datas:
                datas[sv_prn] = {
                    'sv_prn': sv_prn,
                    'srn_max':  message['srn'],
                }
            datas[sv_prn]['el_degree'] = message['el_degree']
            datas[sv_prn]['az_degree'] = message['az_degree']
            datas[sv_prn]['srn'] = message['srn']
            if datas[sv_prn]['srn'] > datas[sv_prn]['srn_max']:
                datas[sv_prn]['srn_max'] = datas[sv_prn]['srn']
            datas[sv_prn]['last_update'] = now

        # 前回から３秒以上経っていたら更新
        if (last_update + timedelta(seconds=3)) < now:
            for sv_prn, data in datas.items():
                # データの更新が５秒以上前であれば、強度を0に
                if (data['last_update'] + timedelta(seconds=5)) < datetime.now(JST):
                    data['srn'] = 0
                    data['last_update'] = now
            update(datas)
            last_update = datetime.now(JST)
except KeyboardInterrupt as e:
    pass