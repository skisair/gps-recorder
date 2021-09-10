
### MOMOのインストール

#### バイナリの取得

cat /proc/cpuinfo | grep "model name"
# model name      : ARMv6-compatible processor rev 7 (v6l)
# model name      : ARMv7 Processor rev 3 (v7l)

export MOMO_VERSION=2021.4.1
export ARM_VERSION=armv6
export FILE_NAME=momo-${MOMO_VERSION}_raspberry-pi-os_${ARM_VERSION}.tar.gz
export DIR_NAME=momo-${MOMO_VERSION}_raspberry-pi-os_${ARM_VERSION}

wget https://github.com/shiguredo/momo/releases/download/2021.4.1/${FILE_NAME} -O momo.tar.gz

tar -zxvf  momo.tar.gz
sudo mv ${DIR_NAME} /opt/momo
sudo apt -y install libSDL2-2.0

./momo --no-audio-device test


#### サービス化
sudo cp momo.service /etc/systemd/system/momo.service

sudo systemctl daemon-reload
sudo systemctl enable momo
sudo systemctl start momo
