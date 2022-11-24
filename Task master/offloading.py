from asyncio import sleep, run, create_task
import asyncio
from collections import deque
from flask import Flask, request
import websockets
import numpy as np
import json
import random
from websockets.legacy.server import WebSocketServerProtocol
import traceback
from MatrixGenerator import generate_matrices

class MachineQueue():
    def __init__(self) -> None:
        self.connected: deque[tuple[int,WebSocketServerProtocol]] = deque()
        self.any_connection = asyncio.Future()
        self.id = 0
    
    def remove(self, element) -> None:
        self.connected.remove(element)
        if self.any_connection.done() and not self.connected:
            self.any_connection = asyncio.Future()
    
    def remove_socket(self,websocket) -> None:
        for machine in self.connected.copy():
            if machine[1] == websocket:
                self.remove(machine)

    def put(self, element) -> None:
        if (isinstance(element, tuple)):
            self.connected.append(element)
        else:
            self.connected.append((self.id, element))
            self.id += 1

        amount_elements = len(self.connected)
        if amount_elements > 0 and not self.any_connection.done():
            self.any_connection.set_result(None)

    def empty(self) -> bool:
        return not self.connected

    def copy(self):
        return self.connected.copy()

    def __iter__(self):
        return self.connected.__iter__()

    def __len__(self):
        return self.connected.__len__()

    def __str__(self) -> str:
        return self.connected.__str__()

    def __getitem__(self, item):
        return self.connected[item]

app = Flask(__name__)
machines: MachineQueue
auction_running: asyncio.Future
# the task queue is a list of pairs where both elements are matrices
task_queue = deque(generate_matrices(amount=2, min_mat_shape=100, max_mat_shape=100, fixed_seed=False))
task_id = 0
prev_winner = None

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
    global machines
    machines.put(websocket)
    try:
        await websocket.wait_closed()
    finally:
        machines.remove_socket(websocket)



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
        First Price Sealed Bid (FPSB)\n""")
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


async def auction_call(offloading_parameters, task):
    global prev_winner, task_id, auction_running
    #Universal part for all auctions
    offloading_parameters["task"] = task
    offloading_parameters["task_id"] = task_id
    offloading_parameters["max_reward"] = random.randrange(1, 11) #change reward calculation eventually
    
    await machines.any_connection
    auction_running = asyncio.Future()
    for machine in machines.copy():
        await machine[1].send(json.dumps((machine[0], offloading_parameters))) #Broadcast the offloading parameters, including the task, to everyone with their respective ids

    receive_tasks = []
    websocketList = [w[1] for w in machines.copy()]
    for connection in websocketList:
        receive_tasks.append(asyncio.create_task(connection.recv())) #Create a task to receive bids from every machine

    print(f'recv 1... machines: {machines}, task: {task_id}')
    finished, unfinished = await asyncio.wait(receive_tasks, timeout=3) #Wait returns the finished and unfinished tasks in the list after the timeout

    received_values = []
    for finished_task in finished:
        received_values.append(json.loads(finished_task.result())) #Place the actual bids into the list

    task_id += 1

    #Depending on the type of auction, call different functions
    if offloading_parameters.get('auction_type') == "SPSB" or offloading_parameters.get('auction_type') == "Second Price Sealed Bid":
        prev_winner, result = await sealed_bid(received_values, task, 2)
        return result
    elif offloading_parameters.get('auction_type') == "FPSB" or offloading_parameters.get('auction_type') == "First Price Sealed Bid":
        prev_winner, result = await sealed_bid(received_values, task, 1)
        return result


async def sealed_bid(received_values, task, price_selector):
    sorted_values = sorted(received_values, key = lambda x:x["bid"])
    #broadcast actual reward to winner, and "you didnt win" to everone else
    #await response from winner

    if (len(sorted_values) > 1): #We should never run an auction with only 1 machine
        lowest_value, second_lowest = sorted_values[0], sorted_values[1]
        reward_value = sorted_values[1]['bid'] if price_selector == 2 else sorted_values[0]['bid'] / 2
        non_winner_sockets = [machine[1] for machine in machines.copy() if machine[0] != lowest_value.get('id')]
        winner = None
        for machine in machines.copy():
            if machine[0] == lowest_value.get('id'):
                winner = machine
                machines.remove(winner)
                if len(non_winner_sockets) > 0:
                    websockets.broadcast(non_winner_sockets, json.dumps({"winner": False}))
                await winner[1].send(json.dumps({"winner": True, "reward": reward_value, "task": task}))
                auction_running.set_result(False)
                result = json.loads(await asyncio.wait_for(winner[1].recv(), timeout=3))
                machines.put(winner)
                return (winner, result)
    else:
        reward_value = sorted_values[0]['bid'] if price_selector == 2 else sorted_values[0]['bid'] / 2
        if machines[0][0] == sorted_values[0].get('id'):
            winner = machines[0]
            machines.remove(winner)
            try:
                await winner[1].send(json.dumps({"winner": True, "reward": reward_value, "task": task}))
                auction_running.set_result(False)
                result = json.loads(await asyncio.wait_for(winner[1].recv(), timeout=5))
            except:
                traceback.print_exc()
                raise
            machines.put(winner)
            return (winner, result)


async def safe_handle_communication(task, offloading_parameters):
    global auction_running
    await machines.any_connection
    if not auction_running.done():
        await auction_running

    result = await handle_communication(task, offloading_parameters)
    return result


async def handle_communication(task, offloading_parameters):
    #Handle the contiuous check of available machines here or earlier
    #This stuff also need to be done concurrently for every single task that comes in
    if offloading_parameters["offloading_type"] == "Auction":
        return await auction_call(offloading_parameters, task)


async def handle_server():
    """Has the server "run in the background" for task offloading to the machines connected."""
    global task_queue
    while True:
        await sleep(0.01)
        # If there is a task and a machine then start a new task by splitting a matrix into vector pairs
        if len(task_queue) != 0 and not machines.empty():
            tasks = [asyncio.create_task(task_handler()) for _ in machines]
            done, pending = await asyncio.wait(tasks)
            task_queue = deque(generate_matrices(amount=7, min_mat_shape=300, max_mat_shape=300, fixed_seed=False))


async def task_handler():
    global task_queue
    task = task_queue.popleft()
    # vector_pairs, array_to_be_filled = split_matrix(task[0], task[1])
    # send vector pairs to machines. 

    results = await safe_send(task)
    # Upon retrieval put the matrix back together and display the result.
    # dot_product_array = fill_array(results, array_to_be_filled)
    print(f'equal: {results == np.matmul(task["mat1"], task["mat2"])}')
    print(f'Clients: {len(machines)}')


async def safe_send(task):
    global auction_running
    """Split vector pairs and safely send the pairs to machines."""
    results = []
    #Potentially wrap this in a block that does a certain amount of tasks or has a certain duration, for easier experiment simulation
    offloading_parameters = await get_offloading_parameters()
    # Create tasks for all the pairs
    auction_running = asyncio.Future()
    auction_running.set_result(None)
    while True:
        try:
            return await asyncio.wait_for(create_task(safe_handle_communication(task, offloading_parameters)), timeout=7)
        except Exception:
            traceback.print_exc()



async def establish_server():
    global machines
    """Start a websocket server on ws://192.168.1.10:5001, upon a new connection call new_connection while the server runs handle_server."""
    host = '192.168.1.10'
    port = 5001
    async with websockets.serve(new_connection, host, port, max_size=None) as websocket:
        machines = MachineQueue()
        await handle_server()


@app.route("/", methods=["POST"])
def receive_task():
    print(request.json)
    return 'ok'


if __name__ == "__main__":
    # Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    # Run establish_server asynchronously 
    run(establish_server())
