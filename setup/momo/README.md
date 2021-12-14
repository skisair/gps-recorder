
### MOMOのインストール
```bash
# バイナリの取得
export MOMO_VERSION=2021.4.1

export VCPU=(`cat /proc/cpuinfo | grep "model name"`)
echo $VCPU
# model name      : ARMv6-compatible processor rev 7 (v6l)
# model name      : ARMv7 Processor rev 3 (v7l)

if [ "`echo $VCPU | grep 'ARMv6'`" ]; then
  export ARM_VERSION=armv6
elif [ "`echo $VCPU | grep 'ARMv7'`" ]; then
  export ARM_VERSION=armv7
elif [ "`echo $VCPU | grep 'ARMv8'`" ]; then
  export ARM_VERSION=armv8
else
  exit 1
fi

export FILE_NAME=momo-${MOMO_VERSION}_raspberry-pi-os_${ARM_VERSION}.tar.gz
export DIR_NAME=momo-${MOMO_VERSION}_raspberry-pi-os_${ARM_VERSION}

wget https://github.com/shiguredo/momo/releases/download/2021.4.1/${FILE_NAME} -O momo.tar.gz

tar -zxvf  momo.tar.gz
sudo mv ${DIR_NAME} /opt/momo
sudo apt -y install libSDL2-2.0

# ./momo --no-audio-device test

#### サービス化
sudo cp momo.service /etc/systemd/system/momo.service

sudo systemctl daemon-reload
sudo systemctl enable momo
sudo systemctl start momo
```
https://github.com/shiguredo/momo/blob/develop/doc/LINUX_VIDEO_DEVICE.md

udevadm info --query=all --name=/dev/video14 | grep ID_SERIAL_SHORT
