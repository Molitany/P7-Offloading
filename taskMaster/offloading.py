from asyncio import sleep, run, wait, create_task
from threading import Thread
from flask import Flask
import websockets
import numpy as np
import traceback
from auction import auction_call
from machineQueue import MachineQueue
from frontEnd import start_frontend
from globals import task_queue 
from json import JSONEncoder

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
    print(f'equal: {results == np.matmul(task.mat1, task.mat2)}')
    print(f'Clients: {len(machines)}')


async def safe_send(task):
    '''Gets the offloading parameters and wraps the auction in a failsafe to start a new auction if the tasks fails'''
    offloading_parameters = await get_offloading_parameters()
    while True:
        try:
            return await handle_communication(task, offloading_parameters)
        except Exception:
            traceback.print_exc()


async def get_offloading_parameters():
    '''Get the offloading parameters for the offloading with inputs from the server console.'''
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
        offloading_parameters["auction_type"] = "SPSB" #input() or "SPSB"

    print("""What frequency of tasks?
    Slow (1/s)
    Medium (5/s) (default)
    Fast (10/s)\n""")
    offloading_parameters["task_frequency"] = "Medium" #input() or "Medium"

    print("""Do the tasks have deadlines?
    No (Default)
    Yes \n""")
    offloading_parameters["deadlines"] = "No" #input() or "No"

    print("""Are there fines for abandoning a job or going over a possible deadline?
    No (default)
    Yes \n""")
    offloading_parameters["fines"] = "No" #input() or "No"

    print("""Is there a max reward for the tasks?
    No (Default) 
    Yes \n""")
    offloading_parameters["max_reward"] = "No" #input() or "No"

    #Simply add more cases to each of these or more categories
    #Handling of types is later and on the machines
    #Stuff likes this can also be split into seperate functions or its own file if needed

    return offloading_parameters


async def handle_communication(task, offloading_parameters):
    '''Start an auction if a machine is available and it is an Auction.'''    
    #Handle the contiuous check of available machines here or earlier
    await machines.any_connection
    if offloading_parameters["offloading_type"] == "Auction":
        return await auction_call(offloading_parameters, task, machines)


if __name__ == "__main__":
    Thread(target=start_frontend, args=()).start()
    run(establish_server()) # Run establish_server asynchronously 
