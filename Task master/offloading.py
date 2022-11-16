from asyncio import sleep, run, Queue, create_task, wait, FIRST_EXCEPTION
import asyncio
from asyncio.exceptions import TimeoutError as AsyncTimeoutError
from collections import deque
from threading import Thread
from flask import Flask, request
import websockets
import numpy as np
import json_numpy
import json
import random
from websockets.exceptions import ConnectionClosed
import auction
import traceback

app = Flask(__name__)
machines_connected = Queue()
machine_id = 0
auction_running: asyncio.Future
matrix1 = np.random.rand(2, 2)
matrix2 = np.random.rand(2, 2)
# the task queue is a list of pairs where both elements are matrices
task_queue = deque([(matrix1, matrix2)])

def split_matrix(a, b):
    """Split the matrix into vector pairs and the specific cell to be multiplied into."""
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
    """Gathers the pairs back into a full matrix post multiplication."""
    for dot_product in dot_products:
        array_to_be_filled[dot_product['cell'][0]][dot_product['cell'][1]] = dot_product['dot_product']
    return array_to_be_filled.tolist()


async def new_connection(websocket):
    """
    Upon a new websocket connection add the machine to the known machines and set it to available\n
    when the connection is disrupted (Timeout, ConnectionClosed, etc.) the machine is removed from the known machines. 
    """
    global machine_id
    await machines_connected.put((machine_id, websocket))
    machine_id += 1
    try:
        await websocket.wait_closed()
    finally:
        for machine in machines_connected._queue:
            if machine[1] == websocket:
                machines_connected._queue.remove(machine)


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
    First come, first server (FCFS) (not implemented)\n""") #We could just define our 4 types here, normal, with fines, with max_reward, both and save some enter
    offloading_parameters["offloading_type"] = "Auction"

    if offloading_parameters["offloading_type"] == "Auction" or offloading_parameters["offloading_type"] == "auction":
        print("""What auction type to use?
        Second Price Sealed Bid (SPSB) (default)
        First Price (not implemented)\n""")
        offloading_parameters["auction_type"] = "SPSB"

    print("""What frequency of tasks?
    Slow (1/s)
    Medium (5/s) (default)
    Fast (10/s)\n""")
    offloading_parameters["task_frequency"] = "Medium"

    print("""Do the tasks have deadlines?
    No (Default)
    Yes \n""")
    offloading_parameters["deadlines"] = "No"

    print("""Are there fines for abandoning a job or going over a possible deadline?
    No (default)
    Yes \n""")
    offloading_parameters["fines"] = "No"

    print("""Is there a max reward for the tasks?
    No (Default) 
    Yes \n""")
    offloading_parameters["max_reward"] = "No"

    #Simply add more cases to each of these or more categories
    #Handling of types is later and on the machines
    #Stuff likes this can also be split into seperate functions or its own file if needed

    return offloading_parameters


async def auction_call(offloading_parameters, task, machines_connected, auction_running: asyncio.Future):
    #Universal part for all auctions
    offloading_parameters["task"] = task
    offloading_parameters["max_reward"] = random.randrange(1, 11) #change reward calculation eventually
    
    for machine in machines_connected:
        await machine[1].send(json.dumps((machine[0], offloading_parameters))) #Broadcast the offloading parameters, including the task, to everyone with their respective ids

    receive_tasks = []
    websocketList = [w[1] for w in machines_connected]
    for connection in websocketList:
        receive_tasks.append(asyncio.create_task(connection.recv())) #Create a task to receive bids from every machine
        
    print(f'recv 1: websockets {websocketList}')
    finished, unfinished = await asyncio.wait(receive_tasks, timeout=3) #Wait returns the finished and unfinished tasks in the list after the timeout

    auction_running.set_result(False)

    received_values = []
    for finished_task in finished:
        received_values.append(json.loads(finished_task.result())) #Place the actual bids into the list

    #Depending on the type of auction, call different functions
    if offloading_parameters.get('auction_type') == "SPSB" or offloading_parameters.get('auction_type') == "Second Price Sealed Bid":
        return await auction.second_price_sealed_bid(received_values, machine, task, machines_connected)


async def safe_handle_communication(pair, offloading_parameters):
    global auction_running
    await auction_running
    machine = await machines_connected.get()
    auction_running = asyncio.Future()
    result = await handle_communication(pair, offloading_parameters, machines_connected._queue.copy()+deque([machine]))
    await machines_connected.put(machine)
    return result

async def handle_communication(pair, offloading_parameters, machines):
    while True:
    #Handle the contiuous check of available machines here or earlier
    #This stuff also need to be done concurrently for every single task that comes in
        if offloading_parameters["offloading_type"] == "Auction":
            return await auction_call(offloading_parameters, pair, machines, auction_running)


async def handle_server():
    """Has the server "run in the background" for task offloading to the machines connected."""
    while True:
        await sleep(0.01)
        # If there is a task and a machine then start a new task by splitting a matrix into vector pairs
        if len(task_queue) != 0 and not machines_connected.empty():
            task = task_queue.popleft()
            vector_pairs, array_to_be_filled = split_matrix(task[0], task[1])
            # send vector pairs to machines. 
            results = await safe_send(vector_pairs)
            # Upon retrieval put the matrix back together and display the result.
            dot_product_array = fill_array(results, array_to_be_filled)
            print(f'we got: {dot_product_array}\n should be: {np.matmul(matrix1, matrix2)}\n'
                  f'equal: {dot_product_array == np.matmul(matrix1, matrix2)}')
            print(f'Clients: {machines_connected.qsize()}')
            task_queue.append((matrix1, matrix2))

async def safe_send(vector_pairs: list):
    global auction_running
    """Split vector pairs and safely send the pairs to machines."""
    sub_tasks = {}
    results = []
    auction_running = asyncio.Future()
    auction_running.set_result(False)
    #Potentially wrap this in a block that does a certain amount of tasks or has a certain duration, for easier experiment simulation
    offloading_parameters = await get_offloading_parameters()
    # Create tasks for all the pairs
    for pair in vector_pairs:
        sub_tasks.update({create_task(safe_handle_communication(pair, offloading_parameters)): pair})
    while len(sub_tasks) != 0:
        try:
            # Run all of the tasks "at once" waiting for 5 seconds then it times out.
            # The wait stops when a task hits an exception or until they are all completed
            done, pending = await wait(sub_tasks.keys(), timeout=7, return_when=FIRST_EXCEPTION)
            for task in done:
                # ConnectionClosedOK is done but also an exception, so we have to check if the task is actually returned a result.
                if task.exception() is None:
                    results.append(task.result())
                    sub_tasks.pop(task)
                else: raise task.exception()
        except Exception as e:
            traceback.print_exc()
        finally:
            # if we are not done then we cancel all of the tasks, as they have been assigned to a machine already, 
            # and create the missing tasks again and try sending the missing pairs again. 
            if sub_tasks != 0:
                map(lambda sub_task: sub_task.cancel(), sub_tasks.keys())
                pairs = list(sub_tasks.copy().values())
                sub_tasks.clear()
                for pair in pairs:
                    sub_tasks.update({create_task(safe_handle_communication(pair, offloading_parameters)): pair})
                    await asyncio.sleep(1)
    return results


async def establish_server():
    """Start a websocket server on ws://192.168.1.10:5001, upon a new connection call new_connection while the server runs handle_server."""
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
    # Run establish_server asynchronously 
    run(establish_server())
