from asyncio import shield, wait_for, sleep, as_completed, run
import asyncio
from collections import deque
import json
import numpy
from flask import Flask, request
from threading import Thread
import websockets
import numpy as np
import json_numpy
from websockets.exceptions import ConnectionClosedError, ConnectionClosed
import auction

app = Flask(__name__)
machines_connected = deque()

matrix1 = np.array([[1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                    [10, 12, 14]])

matrix2 = np.array([[1, 2, 3, 10],
                    [4, 5, 6, 10],
                    [7, 8, 9, 10]])
task_queue = deque([(matrix1, matrix2)])
sub_tasks = {}


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
    machines_connected.append({'ws': websocket, 'available': True})
    try:
        await websocket.wait_closed()
    finally:
        for machine in machines_connected.copy():
            if machine.get('ws') == websocket:
                machines_connected.remove(machine)


async def machine_available(machine):
    while not machine.get('available'):
        await sleep(0.1)


#Do auction with all machines, its their job to respond or not
    #Machines should always be ready to respond and decline
    #Publish task, and receive calculated offers
    #Calculate second lowest offer using equation, and publish the winner ID to everyone
    #Send reward to winner
    #Send task to winner
    #Receive completed task


async def get_offloading_parameters():

    offloading_parameters = {}

    print("""What type of offloading to use?
    Auction (default)
    Contract (not implemented)
    First come, first server (FCFS) (not implemented)\n""")
    offloading_parameters["offloading_type"] = input() or "Auction"

    if offloading_parameters["offloading_type"] == "Auction" or offloading_parameters["offloading_type"] == "auction":
        print("""What auction type to use?
        Second Price Sealed Bid (SPSB) (default)
        First Price (not implemented)\n""")
        auction_type = input()
        offloading_parameters["auction_type"] = input() or "SPSB"

    print("""What frequency of tasks?
    Slow (1/s)
    Medium (5/s) (default)
    Fast (10/s)\n""")
    offloading_parameters["task_frequency"] = input() or "Medium"

    print("""Do the tasks have deadlines?
    Yes
    No (Default)\n""")
    offloading_parameters["deadlines"] = input() or "No"

    #Simply add more cases to each of these or more categories
    #Handling of types is later and on the machines
    #Stuff likes this can also be split into seperate functions or its own file if needed

    return offloading_parameters

async def handle_communication(pair):
    #Potentially wrap this in a block that does a certain amount of tasks or has a certain duration, for easier experiment simulation
    offloading_parameters = get_offloading_parameters()
    
    while True:
        try:
        #Handle the contiuous check of available machines here or earlier
        #This stuff also need to be done concurrently for every single task that comes in
            if offloading_parameters["offloading_type"] == "Auction":
                auction.auction_call(offloading_parameters, pair, machines_connected)
        except (ConnectionClosed, asyncio.exceptions.TimeoutError):
            print(f'a machine disconnected')


async def handle_server():
    while True:
        await sleep(0.1)
        if len(task_queue) != 0 and len(machines_connected) != 0:
            global sub_tasks
            task = task_queue.popleft()
            vector_pairs, array_to_be_filled = split_matrix(task[0], task[1])
            for pair in vector_pairs:
                sub_tasks.update({asyncio.create_task(handle_communication(pair)): pair})
            results = await safe_send()

            dot_product_array = fill_array(results, array_to_be_filled)
            print(f'we got: {dot_product_array}\n should be: {numpy.matmul(matrix1, matrix2)}\n'
                  f'equal: {dot_product_array == numpy.matmul(matrix1, matrix2)}')
            print(f'Clients: {len(machines_connected)}')
            task_queue.append((matrix1, matrix2))


async def safe_send():
    global sub_tasks
    results = []
    while len(sub_tasks) != 0:
        try:
            done, pending = await asyncio.wait(sub_tasks.keys(), timeout=5, return_when=asyncio.FIRST_EXCEPTION)
            for task in done:
                if task.exception() is None:
                    results.append(task.result())
                    sub_tasks.pop(task)
        except (asyncio.exceptions.TimeoutError, ConnectionClosed) as e:
            pass
        finally:
            if sub_tasks != 0:
                map(lambda sub_task: sub_task.cancel(), sub_tasks.keys())
                pairs = list(sub_tasks.copy().values())
                sub_tasks.clear()
                for pair in pairs:
                    sub_tasks.update({asyncio.create_task(handle_communication(pair)): pair})
    return results


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
    # Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    run(establish_server())
