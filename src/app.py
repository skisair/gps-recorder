import pathlib

import streamlit as st
import pandas as pd
from PIL import Image


# {'data_id': 'GPRMC', 'gps_date_time': '2021-06-19T13:51:51', 'lat': 35.375200799999995, 'lng': 139.4160672, 'speed': 0.231, 'mode': 'A', 'device_id': 'ShoheinoAir-2', 'local_time': '20210619225150985617'}

# サイドメニュー表示
# リアルタイム・時系列検索

# 画像表示

# グラフ表示

# データ表示
class DeviceDataset:

    def __init__(self):
        self.data_dir = pathlib.Path('data/c01_p001')
        self.data_id = 'GPRMC'
        self.labels = ['ShoheinoAir-2','DEVICE1']

    def select(self, label: str):
        return list(self.data_dir.glob(f'*'))

def main():
    st.markdown("# Data visualization tool using Streamlit")
    dataset = DeviceDataset()
    selector = st.sidebar.selectbox("Select your device", dataset.labels)
    selected_data = dataset.select(selector)
    index = st.sidebar.number_input(
        f"Select index from 0 to {len(selected_data)}",
        min_value=0,
        max_value=len(selected_data),
        value=0,
        step=1,
    )
    sample_path = selected_data[index]
    image = Image.open(sample_path)
    expand = st.sidebar.checkbox("Expand")
    degree = st.sidebar.slider("Degree", min_value=0, max_value=180, step=1)
    st.image(image.rotate(degree, expand=expand))


if __name__ == "__main__":
    main()