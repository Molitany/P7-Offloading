chmod o+x ./startupServiceEnabler.sh 
chmod o+x ./connectJohanWifi.sh

cp startupServiceEnabler.sh /usr/local/bin/ 
cp delayedStart.py /usr/local/bin/
cp connectJohanWifi.sh /usr/local/bin/

echo "aaunano" | sudo -S /usr/local/bin/startupServiceEnabler.sh

