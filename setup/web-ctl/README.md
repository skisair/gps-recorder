#### サービス化
sudo cp web-ctl.service /etc/systemd/system/web-ctl.service

sudo systemctl daemon-reload
sudo systemctl enable web-ctl
sudo systemctl start web-ctl

sudo systemctl status web-ctl