from concurrent.futures import ThreadPoolExecutor
from networkscan import Networkscan
from flask import Flask, request
from threading import Thread
import asyncio
import websockets
import socket

app = Flask(__name__)
# possible ips ['169.254.10.165', '169.254.34.210', '169.254.48.187', '169.254.71.202']
machine_IPs = {
    "previous": ['169.254.34.210'],
    "current": []
}
task_queue = []

def get_machineIPs():
    local_ip = socket.gethostbyname(socket.gethostname())
    local_network = "169.254.0.0/16"
    while True:
        scan = Networkscan(local_network)   
        scan.run()
        for ips in scan.list_of_hosts_found:
            machine_IPs["previous"] = machine_IPs.get("current")
            if ips != local_ip and ips not in machine_IPs:
                machine_IPs["current"].append(ips)
    
async def establish_connection(ip):
    port = 5001
    async with websockets.connect(f"ws://{ip}:{port}") as websocket:
        await websocket.send(socket.gethostbyname(socket.gethostname()).encode())

@app.route("/", methods=["POST"])
def recieve_task():
    task_queue.append(request.json)
    return 'ok'

if __name__ == "__main__":
    Thread(target=get_machineIPs).start()
    Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    for ip in machine_IPs.get("previous"):
        asyncio.run(establish_connection(ip))
    while True:
            for ip in list(set(machine_IPs.get("current")) - set(machine_IPs.get("previous"))):
                print(f"new ip found: {ip}")
                asyncio.run(establish_connection(ip))