from asyncio import sleep, run, wait, create_task
from threading import Thread
import time
from flask import Flask
import websockets
import numpy as np
import traceback
from auction import auction_call
from machineQueue import MachineQueue
from FlaskApp.frontEnd import start_frontend
from globals import task_queue, client_inputs
from json import JSONEncoder
from taskGenerator import generate_tasks

def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)

_default.default = JSONEncoder().default
JSONEncoder.default = _default

app = Flask(__name__)
machines: MachineQueue
prev_winner = None


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

async def establish_server():
    global machines
    """Start a websocket server on ws://192.168.1.10:5001, upon a new connection call new_connection while the server runs handle_server."""
    host = '192.168.1.10'
    port = 5001
    async with websockets.serve(new_connection, host, port, max_size=None) as websocket:
        machines = MachineQueue()
        await handle_server()


async def handle_server():
    """Has the server "run in the background" for task offloading to the machines connected."""
    await sleep(0.1)
    while True:
        await sleep(0.01)
        # If there is a task and a machine then start a new task by splitting a matrix into vector pairs
        if len(task_queue) != 0 and not machines.empty():
            amount_tasks = min(len(machines), len(task_queue))
            tasks = [create_task(task_handler()) for _ in range(amount_tasks)]
            done, pending = await wait(tasks)


async def task_handler():
    '''Gets a task from the queue and start an auction for it when available.'''
    task = task_queue.popleft() # Get a task from the task queue
    results = await safe_send(task) # Send it to be auctioned
    # Display result
    with open('log', 'a') as f: 
        f.write(f'[{time.asctime(time.localtime(time.time()))}] {results}\n') # add the result to the log with a timestamp
    print(f'equal: {results == np.matmul(task.get("mat1"), task.get("mat2"))}')
    print(f'Clients: {len(machines)}')


async def safe_send(task):
    '''Gets the offloading parameters and wraps the auction in a failsafe to start a new auction if the tasks fails'''
    while True:
        try:
            return await handle_communication(task)
        except Exception:
            traceback.print_exc()


async def handle_communication(task):
    '''Start an auction if a machine is available and it is an Auction.'''    
    #Handle the contiuous check of available machines here or earlier
    await machines.any_connection
    if task.get('offloading_parameters').get("offloading_type") == "Auction":
        return await auction_call(task, machines)

def handle_client_input():
    '''Generate tasks depending on input from the frontend and add them to the queue.'''
    while True:
        if len(client_inputs) > 0:
            client_input = client_inputs.popleft()
            amount = client_input.get('amount')
            frequency = client_input.get('task_frequency')
            batches = int(amount / frequency) if frequency != -1 else 1 # if frequency is no limit then only do the for loop once with the amount as max
            for _ in range(0, batches):
                timer = time.time()
                task_queue.extend(generate_tasks(
                    amount = frequency if frequency != -1 else amount,
                    min_mat_shape = client_input.get('min_mat_shape'),
                    max_mat_shape = client_input.get('max_mat_shape'),
                    min_deadline = client_input.get('min_deadline'),
                    max_deadline = client_input.get('max_deadline'),
                    fixed_seed = client_input.get('fixed_seed'),
                    offloading_parameters = client_input.get('offloading_parameters')
                ))
                time_spent = time.time() - timer
                if time_spent < 1:
                    time.sleep(1 - time_spent)

if __name__ == "__main__":
    try:
        with open('log', 'w') as f: # reset logging
            f.write('')
        Thread(target=start_frontend, args=()).start() # start flask server 
        Thread(target=handle_client_input, args=()).start() # handle client input in a seperate thread so frontend doesn't hang
        run(establish_server()) # Run establish_server asynchronously 
    except Exception:
            traceback.print_exc()
