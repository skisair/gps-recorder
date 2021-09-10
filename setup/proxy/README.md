'http-proxy'

sudo npm install -g http-proxy

cd ~
mkdir reverse_proxy
cd reverse_proxy
npm link http-proxy

sudo node proxy.js


#### サービス化
sudo cp node-proxy.service /etc/systemd/system/node-proxy.service

sudo systemctl daemon-reload
sudo systemctl enable node-proxy
sudo systemctl start node-proxy
