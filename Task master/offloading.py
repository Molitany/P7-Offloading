from collections import deque
import json
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
    timer = 1
    while not machine.get('available'):
        await asyncio.sleep(0.5)
        timer += 1
        if timer == 20:
            return False
    return True


#Do auction with all machines, its their job to respond or not
    #Machines should always be ready to respond and decline
    #Publish task, and receive calculated offers
    #Calculate second lowest offer using equation, and publish the winner ID to everyone
    #Send reward to winner
    #Send task to winner
    #Receive completed task
async def auction_call(offloading_parameters):

    #Universal part for all auctions
    websocketList = [key for m in machines for key in m]
    websockets.broadcast(websocketList, json.dumps(offloading_parameters))

    receive_tasks = []
    for connection in websocketList:
        receive_tasks.append(asyncio.create_task(connection.recv()))

    finished, unfinished = await asyncio.wait(receive_tasks, timeout=3) #Wait returns the finished and unfinished tasks in the list after the timeout

    received_values = []
    for finished_task in finished:
        received_values.append(json.load(finished_task.result()))

    if offloading_parameters["Auction_type"] == "SPSB" or offloading_parameters["Auction_type"] == "Second Price Sealed Bid":
        second_price_sealed_bid(received_values, offloading_parameters)


async def second_price_sealed_bid(received_values, offloading_parameters):

    sorted_values = sorted(received_values, key = lambda x:x["bid"])
    #broadcast actual reward to winner, and "you didnt win" to everone else
    #await response from winner

    




async def get_offloading_parameters():

    offloading_parameters = {}

    print("""What type of offloading to use?
    Auction (default)
    Contract (not implemented)
    First come, first server (FCFS) (not implemented)\n""")
    offloading_parameters["offloading_type"] = input() or "Auction" #the or makes "Auction" a default value

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
        #This stuff also need to be done for every single task that comes in
            if offloading_parameters["offloading_type"] == "Auction":
                auction_call(offloading_parameters)
        except (ConnectionClosed, asyncio.exceptions.TimeoutError):
            print(f'a machine disconnected')


        #     machine = machines.popleft()
        #     machines.append(machine)
        #     await machine_available(machine)
        #     machine['available'] = False
        #     websocket = machine.get('ws')
        #     await websocket.send(json_numpy.dumps(pair))
        #     result = await asyncio.wait_for(websocket.recv(), timeout=3)
        #     machine['available'] = True
        #     return result



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
    async with websockets.serve(new_connection, host, port) as websocket: #I think this might be wrong, the handler is done for each connection, but here we're doing the connections in the handler
        await handle_server()


@app.route("/", methods=["POST"])
def receive_task():
    print(request.json)
    return 'ok'


if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    asyncio.run(establish_server())
