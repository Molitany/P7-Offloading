from asyncio import sleep, run, wait, create_task
from threading import Thread
import time
from flask import Flask
import websockets
import traceback
from auction import auction_call
from machineQueue import MachineQueue
from FlaskApp.frontEnd import start_frontend
from globals import task_queue, client_inputs, late_tasks
from taskGenerator import generate_tasks
from logger import Logger
import shutil
from datetime import datetime

app = Flask(__name__)
machines: MachineQueue
logger = Logger()
connected_machines = 0

# Variables for experiments
# list of id and late amount in a pair [(0, 0.2), (1, 5.3)...]
completed_tasks: int = 0
start_fog_timer: float = time.time()
start_client_timer: float = 0
start_machine_timer: float = 0

async def new_connection(websocket):
    """
    Upon a new websocket connection add the machine to the known machines and set it to available\n
    when the connection is disrupted (Timeout, ConnectionClosed, etc.) the machine is removed from the known machines. 
    """
    global machines
    machines.put(websocket)
    logger.log_message(f'New device connected, new amount: {len(machines)}')
    try:
        await websocket.wait_closed()
    finally:
        logger.log_message(f'Device disconnected, new amount: {len(machines)}')
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
            tasks = [create_task(task_handler()) for _ in task_queue]
            await wait(tasks)
        if len(task_queue) == 0 and completed_tasks > 0:
            log_task()


async def task_handler():
    '''Gets a task from the queue and start an auction for it when available.'''
    task = task_queue.popleft()  # Get a task from the task queue
    await safe_send(task)  # Send it to be auctioned


async def safe_send(task):
    '''Gets the offloading parameters and wraps the auction in a failsafe to start a new auction if the tasks fails'''
    while True:
        try:
            return await handle_communication(task)
        except Exception:
            traceback.print_exc()


async def handle_communication(task):
    '''Start an auction if a machine is available and it is an Auction.'''
    global completed_tasks, start_machine_timer
    # Handle the contiuous check of available machines here or earlier
    await machines.any_connection
    if task.get('offloading_parameters').get("offloading_type") == "Auction":
        unpacked = await auction_call(task, machines)
        if isinstance(unpacked, tuple):
            start_machine_timer, res = unpacked
            completed_tasks += 1
            logger.log_message('task recieved')
            return res


def handle_client_input():
    '''
    Generate tasks depending on input from the frontend and add them to the queue.\n
    Sends the requested tasks in batches to handle task frequency (1/sec, 5/sec...) and waits if the batch hasn't taken 1 second yet.
    '''
    global connected_machines, start_client_timer
    while True:
        if len(client_inputs) > 0:
            start_client_timer = time.time()
            connected_machines = len(machines)
            client_input = client_inputs.popleft()
            amount = client_input.get('amount')
            frequency = client_input.get('task_frequency')
            logger.log_message(f'new input {{frequency: {frequency}/sec}}')
            # if frequency is no limit then only do the for loop once with the amount as max
            batches = max(int(amount / frequency), 1)
            for _ in range(0, batches):
                timer = time.time()
                task_queue.extend(generate_tasks(
                    amount=frequency if frequency == -1 or frequency < amount else amount,
                    min_mat_shape=client_input.get('min_mat_shape'),
                    max_mat_shape=client_input.get('max_mat_shape'),
                    min_deadline=client_input.get('min_deadline'),
                    max_deadline=client_input.get('max_deadline'),
                    fixed_seed=client_input.get('fixed_seed'),
                    offloading_parameters=client_input.get(
                        'offloading_parameters')
                ))
                time_spent = time.time() - timer
                if time_spent < 1:
                    time.sleep(1 - time_spent)

def log_task():
    global completed_tasks, start_machine_timer,start_fog_timer, start_client_timer, late_tasks
    logger.log_colored_message(logger.colors.GREEN, f'Number of tasks: {completed_tasks}')
    logger.log_colored_message(logger.colors.GREEN, 
                f'Fog Throughput: {completed_tasks / (time.time() - start_fog_timer)}')
    logger.log_colored_message(logger.colors.GREEN, 
                f'Client Throughput: {completed_tasks / (time.time() - start_client_timer)}')
    logger.log_colored_message(logger.colors.GREEN, 
                f'Machine Throughput: {completed_tasks / (time.time() - start_machine_timer)}')
    logger.log_colored_message(logger.colors.GREEN, 
                f'late tasks: {len(late_tasks)/completed_tasks*100}%')
    logger.log_colored_message(logger.colors.GREEN, 
                f'Sum of task delays: {sum([delay[1] for delay in late_tasks])}')
    logger.log_colored_message(logger.colors.GREEN, f'Clients connected: {connected_machines}')
    shutil.copyfile('log.txt', f'logs/finished_log {datetime.today().isoformat(sep=" ", timespec="seconds")}.txt')
    completed_tasks = 0
    late_tasks = []
    start_fog_timer = time.time()
    logger.truncate()

if __name__ == "__main__":
    try:
        logger.truncate()
        Thread(target=start_frontend, args=()).start()  # start flask server
        # handle client input in a seperate thread so frontend doesn't hang
        Thread(target=handle_client_input, args=()).start()
        run(establish_server())  # Run establish_server asynchronously
    except:
        logger.log_error(f'General Error: {traceback.print_exc()}')
        
