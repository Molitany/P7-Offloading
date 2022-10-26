from collections import deque
import numpy
from flask import Flask, request
from threading import Thread
import asyncio
import websockets
import numpy as np
import json_numpy
from websockets.exceptions import ConnectionClosedError, ConnectionClosed

app = Flask(__name__)
machines = deque()

matrix1 = np.array([[1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                    [10, 12, 14]])

matrix2 = np.array([[1, 2, 3, 10],
                    [4, 5, 6, 10],
                    [7, 8, 9, 10]])
task_queue = deque([(matrix1, matrix2)])


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
    machines.append({'ws': websocket, 'available': True})
    try:
        await websocket.wait_closed()
    finally:
        for machine in machines.copy():
            if machine.get('ws') == websocket:
                machines.remove(machine)


async def machine_available(machine):
    while not machine.get('available'):
        await asyncio.sleep(0.5)


async def handle_communication(pair):
    while True:
        try:
            machine = machines.popleft()
            machines.append(machine)
            await machine_available(machine)
            machine['available'] = False
            websocket = machine.get('ws')
            await websocket.send(json_numpy.dumps(pair))
            result = await asyncio.wait_for(websocket.recv(), timeout=3)
            machine['available'] = True
            return result
        except (ConnectionClosed, asyncio.exceptions.TimeoutError):
            print(f'machine {machine} disconnected')


async def handle_server():
    while True:
        await asyncio.sleep(0.5)
        if len(task_queue) != 0 and len(machines) != 0:
            task = task_queue.popleft()
            vector_pairs, array_to_be_filled = split_matrix(task[0], task[1])
            result = []
            for f in asyncio.as_completed([handle_communication(pair) for pair in vector_pairs]):
                result.append(json_numpy.loads(await f))
            dot_product_array = fill_array(result, array_to_be_filled)
            print(f'we got: {dot_product_array}\n should be: {numpy.matmul(task[0], task[1])}')
            print(f'Clients: {len(machines)}')
            task_queue.append((matrix1, matrix2))


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
    asyncio.run(establish_server())
