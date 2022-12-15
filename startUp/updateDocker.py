import os
import re

scan = os.popen('nmap -sn 192.168.1.0/24').read()

ips = re.findall('Nmap scan report for ([\d.]+?)\n', scan)

for ip in ips:
    os.popen(f"ssh -o 'StrictHostKeyChecking=no' aaunano@{ip} 'echo aaunano | sudo -S connectDockerAndWifi.sh'")