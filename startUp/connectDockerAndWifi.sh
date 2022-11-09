#!/bin/bash

echo "aaunano" | sudo -S ifconfig wlan0 up
nmcli radio wifi on
echo "aaunano" | sudo -S nmcli dev wifi connect Johan
sleep 4
sudo docker build https://github.com/JohanThomsen/P7-Offloading-Docker.git#main -t handler
sudo docker rm -f handler
sudo docker run -t -d --name handler handler

