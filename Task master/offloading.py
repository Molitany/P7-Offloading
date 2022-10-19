import concurrent
from multiprocessing import Process

from flask import Flask, request
from threading import Thread
import asyncio
import websockets
import os

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether, ARP, srp
from scapy.sendrecv import sr

app = Flask(__name__)
machine_ips = {
    "alive": [],
    "potential": []
}
servers_open = {}
task_queue = []


async def get_machine_ips():
    local_network = "192.168.1.0/24"
    temp_dict = {
        "alive": [],
        "potential": []
    }
    ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=local_network), timeout=2, iface="eno1")
    if len(ans) != 0:
        for ip in ans:
            temp_dict['potential'].append(ip.answer.psrc)
        temp_dict['alive'] = machine_ips.get('alive')
        machine_ips.update(temp_dict)


async def establish_connection(ip):
    host = os.popen(
        'ip addr show eno1 | grep "\<inet\>" | awk \'{ print $2 }\' | awk -F "/" \'{ print $1 }\'').read().strip()
    port = 5001
    async with websockets.connect(f"ws://{ip}:{port}") as websocket:
        await websocket.send(host.encode())
        await asyncio.Future()


@app.route("/", methods=["POST"])
def receive_task():
    print(request.json)
    return 'ok'


def find_alive_ips():
    port = 5001
    while True:
        asyncio.run(get_machine_ips())
        if len(machine_ips.get("potential")) != 0:
            for ip in machine_ips.get("potential"):
                print(f"new ip found: {ip}, checking if server is up")
                ans, unans = sr(IP(dst=ip) / TCP(dport=port, flags="S"))
                if 'R' not in str(ans[0].answer.payload.fields.get('flags')):
                    print(f'server is alive on {ip}\n')
                    if ip not in machine_ips.get('alive'):
                        machine_ips['alive'].append(ip)
                else:
                    print(f'server is dead on {ip}\n')
                    if ip in machine_ips.get('alive'):
                        machine_ips['alive'].remove(ip)
                        server = servers_open.pop(ip, None)
                        if server is not None:
                            server.terminate()


def main():
    Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    Thread(target=find_alive_ips).start()
    while True:
        for ip in machine_ips.get('alive'):
            if ip not in servers_open:
                process = Process(target=asyncio.run, args=(establish_connection(ip),))
                process.start()
                servers_open.update({ip: process})


if __name__ == "__main__":
    main()
