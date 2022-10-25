from collections import deque

import numpy
from flask import Flask, request
from threading import Thread
import asyncio
import websockets
import numpy as np
import json_numpy

# from scapy.layers.inet import IP, TCP
# from scapy.layers.l2 import Ether, ARP, srp
# from scapy.sendrecv import sr

app = Flask(__name__)
# machine_ips = {
#     "alive": [],
#     "potential": []
# }
clients = deque()

matrix1 = np.array([[1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                    [10, 12, 14]])

matrix2 = np.array([[1, 2, 3, 10],
                    [4, 5, 6, 10],
                    [7, 8, 9, 10]])
task_queue = deque([(matrix1, matrix2)])


# async def get_machine_ips():
#     local_network = "192.168.1.0/24"
#     temp_dict = {
#         "alive": [],
#         "potential": []
#     }
#     ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=local_network), timeout=2, iface="eno1")
#     if len(ans) != 0:
#         for ip in ans:
#             temp_dict['potential'].append(ip.answer.psrc)
#         temp_dict['alive'] = machine_ips.get('alive')
#         machine_ips.update(temp_dict)
#
#
# def find_alive_ips():
#     port = 5001
#     while True:
#         asyncio.run(get_machine_ips())
#         if len(machine_ips.get("potential")) != 0:
#             for ip in machine_ips.get("potential"):
#                 print(f"new ip found: {ip}, checking if server is up")
#                 ans, unans = sr(IP(dst=ip) / TCP(dport=port, flags="S"), inter=0.5, retry=-2, timeout=1)
#                 if len(ans) != 0:
#                     if 'R' not in str(ans[0].answer.payload.fields.get('flags')):
#                         print(f'server is alive on {ip}\n')
#                         if ip not in machine_ips.get('alive'):
#                             machine_ips['alive'].append(ip)
#                     else:
#                         print(f'server is dead on {ip}\n')
#                         if ip in machine_ips.get('alive'):
#                             machine_ips['alive'].remove(ip)
#                             server = servers_open.pop(ip, None)
#                             if server is not None:
#                                 server.terminate()

def split_matrix(a, b):
    array_to_be_filled = np.zeros((np.shape(a)[0], np.shape(b)[1]))
    vector_pairs = []
    if np.shape(a)[1] == np.shape(b)[0]:
        for i in range(0, np.shape(a)[0]):
            for j in range(0, np.shape(b)[1]):
                vector_pairs.append({'vector': [a[i, :].tolist(), b[:, j].tolist()],
                                     'cell': [i, j]})
    else:
        print('illegal vector multiplication')
    return vector_pairs, array_to_be_filled


def fill_array(dot_products, array_to_be_filled):
    for dot_product in dot_products:
        array_to_be_filled[dot_product['cell'][0]][dot_product['cell'][1]] = dot_product['dot_product']
    return array_to_be_filled.tolist()


async def new_connection(websocket):
    clients.append({'ws': websocket, 'available': True})
    try:
        await websocket.wait_closed()
    finally:
        for client in clients:
            if client.get('ws') == websocket:
                clients.remove(client)


async def client_available(client):
    while not client.get('available'):
        await asyncio.sleep(1)


async def handle_communication(pair):
    client = clients.popleft()
    clients.append(client)
    await client_available(client)
    client['available'] = False
    ws = client.get('ws')
    await ws.send(json_numpy.dumps(pair))
    result = await ws.recv()
    client['available'] = True
    return result


async def handle_server():
    while True:
        await asyncio.sleep(1)
        if len(task_queue) != 0 and len(clients) != 0:
            task = task_queue.popleft()
            vector_pairs, array_to_be_filled = split_matrix(task[0], task[1])
            result = []
            for f in asyncio.as_completed([handle_communication(pair) for pair in vector_pairs]):
                result.append(json_numpy.loads(await f))
            dot_product_array = fill_array(result, array_to_be_filled)
            print(f'we got: {dot_product_array}\n should be: {numpy.matmul(task[0], task[1])}')


async def establish_server():
    host = '192.168.1.10'
    port = 5001
    async with websockets.serve(new_connection, host, port) as websocket:
        await handle_server()


@app.route("/", methods=["POST"])
def receive_task():
    print(request.json)
    return 'ok'


if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    # Thread(target=find_alive_ips).start()
    asyncio.run(establish_server())
