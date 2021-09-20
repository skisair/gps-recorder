export HOST_NAME=raspi4-001

# ホスト名変更
sudo raspi-config nonint do_hostname ${HOST_NAME}

# Serial設定
sudo sh -c "echo '[all]' >> /boot/config.txt"
sudo sh -c "echo 'enable_uart=1' >> /boot/config.txt"
sudo sh -c "echo 'dtoverlay=miniuart-bt' >> /boot/config.txt"
sudo sh -c "echo 'core_freq=250' >> /boot/config.txt"

# 開発ツール導入
sudo apt update
sudo apt -y upgrade
sudo apt install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        libatlas-base-dev \
        libjasper-dev \
        python-opencv \
        python3-distutils \
        git \
        nodejs \
        npm

# Pythonのリンク変更
python --version
cd /usr/bin
ls -l /usr/bin | grep python
sudo unlink python
sudo ln -s python3 python

# PIPインストール
cd ~/
curl -O https://bootstrap.pypa.io/get-pip.py
python get-pip.py
touch ~/.bash_profile
echo -e "# pip paths" >> ~/.bash_profile
echo 'export PATH="/home/pi/.local/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile

# Node.jsインストール
sudo npm cache clean
sudo npm install npm n -g
sudo n stable

# SORACOM設定
# https://users.soracom.io/ja-jp/guides/devices/general/raspberry-pi-dongle/
curl -O https://soracom-files.s3.amazonaws.com/setup_air.sh
sudo bash setup_air.sh
sudo reboot -h now




