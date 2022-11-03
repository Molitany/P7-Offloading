#!/bin/bash

echo "aaunano" | sudo -S ifconfig wlan0 up
nmcli radio wifi on
echo "aaunano" | sudo -S nmcli dev wifi connect Johan
