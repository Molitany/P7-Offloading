#!/bin/bash
userdel start
groupdel start

sudo addgroup --system start
sudo adduser --system --no-create-home --disabled-login --disabled-password --ingroup start start

echo "aaunano" | sudo -S usermod -aG root start


sudo touch /lib/systemd/system/start.service
sudo echo "[Unit]" >| /lib/systemd/system/start.service
sudo echo "After=systemd-update-utmp.service" >> /lib/systemd/system/start.service
sudo echo "After=rc-local.service" >> /lib/systemd/system/start.service
sudo echo "After=rc-network.service" >> /lib/systemd/system/start.service
sudo echo "Before=getty.target" >> /lib/systemd/system/start.service
sudo echo "IgnoreOnIsolate=yes" >> /lib/systemd/system/start.service
sudo echo "Description=\"Startup service\"" >> /lib/systemd/system/start.service
sudo echo "[Service]" >> /lib/systemd/system/start.service
sudo echo "ExecStart=/usr/bin/env python3 /usr/local/bin/delayedStart.py" >> /lib/systemd/system/start.service
sudo echo "Type=oneshot" >> /lib/systemd/system/start.service
sudo echo "User=root" >> /lib/systemd/system/start.service
sudo echo "[Install]" >> /lib/systemd/system/start.service
sudo echo "WantedBy=sysinit.target" >> /lib/systemd/system/start.service

sudo systemctl daemon-reload
sudo systemctl start start
sleep 7
sudo systemctl status start
sudo systemctl enable start
