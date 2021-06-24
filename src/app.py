import os
import pathlib
from datetime import datetime, timezone, timedelta, time
import base64

import streamlit as st
import numpy as np
import cv2

import plotly.graph_objects as go

import pandas as pd
import paho.mqtt.client as mqtt
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import EntityProperty
from geopy.distance import geodesic
import pydeck as pdk

from session import _get_state

JST = timezone(timedelta(hours=+9), 'JST')


# データ表示
class DeviceDataset:
    def __init__(self):
        self.data_dir = pathlib.Path('data/c01_p001')
        self.tdata_table_name = 'tdata'
        self.mdevice_table_name = 'mdevice'

    def get_device_list(self, state):
        device_list = {}
        tasks = state.table_service.query_entities(self.mdevice_table_name)
        for task in tasks:
            if task['device_id'] in device_list:
                pass
            else:
                device_list[task['device_id']] = task
        return list(device_list.keys())

    def get_dataset_list(self, device_id):
        # TODO データリストのAzuriteからの取得
        return ['GPRMC', 'GPVTG', 'GPGGA', 'GPGSA', 'GPGSV', 'GPGLL']

    def select(self, device_id: str, data_id: str, state):
        if state.realtime:
            state.from_key = datetime.now(JST).strftime('%Y%m%d') + state.from_time.strftime('%H%M%S%f')
            state.to_key = (datetime.now(JST) + timedelta(hours=1)).strftime('%Y%m%d%H%M%S%f')
        else:
            state.from_key = state.date_filter[0].strftime('%Y%m%d') + state.from_time.strftime('%H%M%S%f')
            if len(state.date_filter) == 1:
                state.to_key = state.date_filter[0].strftime('%Y%m%d') + state.to_time.strftime('%H%M%S%f')
            else:
                state.to_key = state.date_filter[1].strftime('%Y%m%d') + state.to_time.strftime('%H%M%S%f')

        partition_key = device_id + '_' + data_id
        filter_query = f"PartitionKey eq '{partition_key}' and RowKey gt '{state.from_key}' and RowKey lt '{state.to_key}'"
        tasks = state.table_service.query_entities(self.tdata_table_name, filter=filter_query)
        result = []
        for task in tasks:
            record = {}
            task['local_time'] = datetime.strptime(task['local_time'], '%Y%m%d%H%M%S%f')
            del task['PartitionKey']
            del task['RowKey']
            del task['Timestamp']
            del task['etag']
            del task['device_id']
            del task['data_id']
            if 'gps_date_time' in task:
                del task['gps_date_time']
            for key in task:
                value = task[key]
                if type(value) == EntityProperty:
                    value = task[key].value
                record[key] = value
            result.append(record)
        print(f'query:{filter_query} len:{len(result)}')

        partition_key = device_id + '_' + 'CAM01'
        filter_query = f"PartitionKey eq '{partition_key}' and RowKey gt '{state.from_key}' and RowKey lt '{state.to_key}'"
        select_columns = 'RowKey'
        tasks = state.table_service.query_entities(self.tdata_table_name, filter=filter_query, select=select_columns)
        image_rowkey = []
        for task in tasks:
            image_rowkey.append(task['RowKey'])

        df = pd.DataFrame(result)
        if len(result) > 0:
            df = df.set_index('local_time')
            df = df.sort_index(ascending=False,)
        return {
            'datas': df,
            #'picts': list(self.data_dir.glob(f'*')),
            'picts': image_rowkey,
        }


def display_sidebar(dataset:DeviceDataset, state):

    st.sidebar.subheader("Device and Dataset")
    state.device_id = st.sidebar.selectbox("Device", dataset.get_device_list(state))
    state.data_id = st.sidebar.selectbox("Dataset", dataset.get_dataset_list(state.device_id))
    state.realtime = st.sidebar.checkbox('Realtime')
    st.sidebar.subheader("Filters")
    if state.realtime:
        state.from_time = st.sidebar.time_input(
            "Time From", state.from_time if state.from_time else time(0, 0)
        )
        state.to_time = time(23, 59)
    else:
        state.date_filter = st.sidebar.date_input(
            "From date - To date",
            (
                state.date_filter[0]
                if state.date_filter and len(state.date_filter) == 2
                else datetime.now(JST),
                state.date_filter[1]
                if state.date_filter and len(state.date_filter) == 2
                else datetime.now(JST),
            ),
        )

        first_column, second_column = st.sidebar.beta_columns(2)
        state.from_time = first_column.time_input(
            "From time", state.from_time if state.from_time else time(0, 0)
        )
        state.to_time = second_column.time_input(
            "To time", state.to_time if state.to_time else time(23, 59)
        )


state = _get_state()
dataset = DeviceDataset()


CONNECTION_STRING = \
    'DefaultEndpointsProtocol=http;' \
    'AccountName=devstoreaccount1;' \
    'AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;' \
    'BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;' \
    'QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;' \
    'TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;'

MQTT_CLIENT_ID = os.environ.get('MQTT_CLIENT_ID', default='app')
MQTT_HOST = os.environ.get('MQTT_HOST', default='localhost')
MQTT_PORT = int(os.environ.get('MQTT_PORT', default=1883))
MQTT_KEEP_ALIVE = int(os.environ.get('MQTT_KEEP_ALIVE', default=60))


def on_message(client, userdata, message):
    st.info(message)
    print(message)


def on_connect(client, userdata, flags, respons_code):
    print(f'connected to mqtt server:{respons_code}')
    if respons_code == 0:
        state.mqtt_connected = True


#@st.cache(allow_output_mutation=True)
def restore_client(topic):
    print('mqtt restore_client')
    mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
    mqtt_client.topic = topic
    mqtt_client.connect(MQTT_HOST, MQTT_PORT)
    return mqtt_client


def get_mqtt_client(topic):
    print('mqtt get_mqtt_client')
    mqtt_client = restore_client(topic)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    return mqtt_client


def open_image(device_id, row_key):
    partition_key = device_id + '_' + 'CAM01'

    filter_query = f"PartitionKey eq '{partition_key}' and RowKey eq '{row_key}'"
    select_columns = 'image'
    tasks = state.table_service.query_entities('tdata', filter=filter_query, select=select_columns)
    for task in tasks:
        jpg_as_text = task['image'].encode()
    jpg_original = base64.b64decode(jpg_as_text)
    jpg_as_np = np.frombuffer(jpg_original, dtype=np.uint8)
    image_buffer = cv2.imdecode(jpg_as_np, cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image_buffer, cv2.COLOR_BGR2RGB)
    return image


def get_pict_index(row_keys , pict_time:datetime ):
    pict_key = pict_time.strftime('%Y%m%d%H%M%S%f')
    for i, key in enumerate(row_keys):
        if key >= pict_key:
            break
    return i


def main():
    st.set_page_config(page_title='GPS RECORDER')
    st.title('GPS RECORDER')

    connect_string = os.environ.get('AZURE_STORAGE_CONNECT_STRING', default=CONNECTION_STRING)
    if state.table_service is None:
        state.table_service = TableService(connection_string=connect_string)

    display_sidebar(dataset, state)

    pd.options.display.float_format = '{:.6f}'.format
    # mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
    topic = 'sensor/{device_id}/{data_id}'.format(device_id=state.device_id, data_id=state.data_id)
    mqtt_client = get_mqtt_client(topic)
    timeout = 30
    while not mqtt_client.is_connected() and timeout:
        print('not connected.')
        mqtt_client.loop(timeout=1)
        timeout -= 1

    left_column, right_column = st.beta_columns(2)

    state.selected_datas = dataset.select(state.device_id, state.data_id, state)
    if len(state.selected_datas['picts']) > 0:
        pict_index = state.pict_index if state.pict_index else 0
        pict_time = datetime.strptime(state.selected_datas['picts'][pict_index], '%Y%m%d%H%M%S%f').replace(tzinfo=JST)
        image = open_image(state.device_id, state.selected_datas['picts'][pict_index])
        left_column.image(image)

        from_time = datetime.strptime(state.selected_datas['picts'][0], '%Y%m%d%H%M%S%f').replace(tzinfo=JST)
        to_time = datetime.strptime(state.selected_datas['picts'][-1], '%Y%m%d%H%M%S%f').replace(tzinfo=JST)
        step = timedelta(seconds=1)

        state.pict_time = left_column.slider('camera time', min_value=from_time, max_value=to_time, value=pict_time, step=step, format='YYYY/MM/DD HH:mm:ss')
        state.pict_index = get_pict_index(state.selected_datas['picts'], state.pict_time)
        # st.info(f'{state.from_key}-{state.to_key}')

    df = state.selected_datas['datas']
    if len(df.index) > 0:
        if 'lat' in df.columns:
            right_column.info(f"lat:{df['lat'][0]}")
            right_column.info(f"lon:{df['lon'][0]}")

        state.view_type = st.sidebar.selectbox("type", ['Spread', 'Graph', 'Map', 'Lat-Lon'])

        if state.view_type == 'Spread':
            st.dataframe(df)
        elif state.view_type == 'Map':
            if 'lat' in df.columns:
                # st.map(df)

                lons = df['lon'].values
                lats = df['lat'].values

                lon_center = np.average(lons)
                lat_center = np.average(lats)
                df_map = df[['lon', 'lat']]

                st.pydeck_chart(pdk.Deck(
                    map_style='mapbox://styles/mapbox/streets-v11',
                    initial_view_state=pdk.ViewState(
                        latitude=lat_center,
                        longitude=lon_center,
                        zoom=18,
                        pitch=0,
                    ),
                    layers=[
                        pdk.Layer(
                            'ScatterplotLayer',
                            df_map,
                            get_position='[lon, lat]',
                            get_radius=1,
                            get_fill_color=[255, 140, 0],
                            get_line_color=[0, 0, 0],
                        ),
                    ],
                ))

                path = []
                for index, row in df_map.iterrows():
                    path.append([row['lon'], row['lat']])

                data = [
                    {
                        'name' : 'GPS Track',
                        'color': [255, 140, 0],
                        'path': path,
                    }
                ]

                st.pydeck_chart(pdk.Deck(
                    map_style='mapbox://styles/mapbox/streets-v11',
                    initial_view_state=pdk.ViewState(
                        latitude=lat_center,
                        longitude=lon_center,
                        zoom=18,
                        pitch=0,
                    ),
                    layers=[
                        pdk.Layer(
                            type='PathLayer',
                            data=data,
                            width_scale=1,
                            get_color='color',
                            pickable=True,
                            get_path='path',
                            get_width=1,
                        ),
                    ],
                ))



            else:
                st.info('no lat/lon info in data frame.')
        elif state.view_type == 'Graph':
            figure = create_graph(df)
            st.plotly_chart(figure)
        elif state.view_type == 'Lat-Lon':
            if 'lat' in df.columns:
                figure = get_lat_lon_figure(df)
                st.plotly_chart(figure)
                figure2 = get_lat_lon_figure_org(df)
                st.plotly_chart(figure2)
            else:
                st.info('no lat/lon info in data frame.')
        # df = df.rename(columns={'lng': 'lon'})
        # st.map(df)
    # mqtt_client.loop_forever()
    state.sync()
    # mqtt_client.loop_forever()


def get_lat_lon_figure(df):
    figure = go.Figure()
    '''
    X Lon
    Y Lat
    '''
    lons = df['lon'].values
    lats = df['lat'].values

    lon_center = np.average(lons)
    lat_center = np.average(lats)
    center = (lat_center, lon_center)

    x = []
    y = []
    for lon, lat in zip(lons, lats):
        x_distance = (lat_center, lon)
        y_distance = (lat, lon_center)
        x_dis = geodesic(center, x_distance).meters
        if lon < lon_center:
            x_dis = -x_dis
        y_dis = geodesic(center, y_distance).meters
        if lat < lat_center:
            y_dis = -y_dis
        x.append(x_dis)
        y.append(y_dis)

    range_max = np.ceil(np.max([np.max(np.abs(x)),np.max(np.abs(y))]))

    text = []

    for i in df.index:
        text.append(i.strftime('%Y/%m/%d %H:%M:%S'))

    figure.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines+markers',
        text=text,
        textposition='top center',
        name='lat/lon'))

    figure.update_layout(
        xaxis=dict(range=[-range_max , range_max]),
        yaxis=dict(range=[-range_max, range_max]),
        margin=dict(l=5, r=5, t=5, b=5),
        font=dict(
            size=10,
        )
    )
    return figure


def get_lat_lon_figure_org(df):
    figure = go.Figure()
    '''
    X Lon
    Y Lat
    '''
    x = df['lon'].values
    y = df['lat'].values
    text = []
    for i in df.index:
        text.append(i.strftime('%Y/%m/%d %H:%M:%S'))
    figure.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines+markers',
        text=text,
        textposition='top center',
        name='lat/lon'))
    figure.update_layout(
        margin=dict(l=5, r=5, t=5, b=5),
        font=dict(
            size=10,
        )
    )
    return figure


def create_graph(df):
    figure = go.Figure()
    for col in df.columns:
        if col not in ['local_time', 'gps_date_time']:
            figure.add_trace(go.Scatter(x=df.index, y=df[col], name=col))

        figure.update_layout(
            margin=dict(l=5, r=5, t=5, b=5),
            font=dict(
                size=10,
            ),
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": -0.5,
                "xanchor": "center",
                "x": 0.5,
            },
            xaxis=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=1,
                             label="1m",
                             step="minute",
                             stepmode="backward"),
                        dict(count=10,
                             label="10m",
                             step="minute",
                             stepmode="backward"),
                        dict(count=1,
                             label="1h",
                             step="hour",
                             stepmode="backward"),
                        dict(count=1,
                             label="1d",
                             step="day",
                             stepmode="backward"),
                    ])
                ),
                rangeslider=dict(
                    visible=True
                ),
                type="date"
            )
        )
    return figure


if __name__ == "__main__":
    main()