import os
import pathlib
from datetime import datetime, timezone, timedelta, time

import streamlit as st

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

import pandas as pd
from PIL import Image
import paho.mqtt.client as mqtt
from azure.cosmosdb.table.tableservice import TableService

from session import _get_state

JST = timezone(timedelta(hours=+9), 'JST')

# リアルタイム・時系列検索

# グラフ表示

# データ表示
class DeviceDataset:
    def __init__(self):
        self.data_dir = pathlib.Path('data/c01_p001')
        self.tdata_table_name = 'tdata'

    def get_device_list(self):
        return ['ShoheinoAir-2']

    def get_dataset_list(self, device_id):
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
        print(filter_query)
        tasks = state.table_service.query_entities(self.tdata_table_name, filter=filter_query)
        result = []
        for task in tasks:
            task['local_time'] = datetime.strptime(task['local_time'], '%Y%m%d%H%M%S%f')
            del task['PartitionKey']
            del task['RowKey']
            del task['Timestamp']
            del task['etag']
            del task['device_id']
            del task['data_id']
            result.append(task)
        df = pd.DataFrame(result)
        return {
            'datas': df,
            'picts': list(self.data_dir.glob(f'*')),
        }


def display_sidebar(dataset:DeviceDataset, state):
    st.sidebar.subheader("Device and Dataset")
    state.device_id = st.sidebar.selectbox("Device", dataset.get_device_list())
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


def main():
    connect_string = os.environ.get('AZURE_STORAGE_CONNECT_STRING', default=CONNECTION_STRING)
    if state.table_service is None:
        state.table_service = TableService(connection_string=connect_string)

    st.set_page_config(page_title='GPS RECORDER')
    st.title('GPS RECORDER')
    display_sidebar(dataset, state)
    state.selected_datas = dataset.select(state.device_id, state.data_id, state)
    left_column, right_column = st.beta_columns(2)
    pict_index = state.pict_index if state.pict_index else 0
    image = Image.open(state.selected_datas['picts'][pict_index])
    left_column.image(image)
    state.pict_index = left_column.slider('index',min_value=0, max_value=len(state.selected_datas['picts']), step=1)
    # st.info(f'{state.from_key}-{state.to_key}')
    df = state.selected_datas['datas']
    if len(df.index) > 0:
        right_column.dataframe(df)
        figure = go.Figure()
        for col in df.columns:
            if col not in ['local_time','gps_date_time']:
                figure.add_trace(go.Scatter(x=df['local_time'], y=df[col], name=col))
            figure.update_layout(
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

        st.plotly_chart(figure)


if __name__ == "__main__":
    main()