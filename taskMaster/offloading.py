import asyncio
import json
import shutil
import logging
import time
import traceback
from asyncio import Future, create_task, run, sleep, wait
from datetime import datetime
from threading import Thread

import uvloop
import websockets.client
import websockets.server
from auction import auction_call, auction_result, handle_bid
from FlaskApp.frontEnd import start_frontend
from globals import auctions, client_inputs, late_tasks, machines, task_queue, results
from logger import Logger
from taskGenerator import generate_tasks

logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG,
)

logger = Logger()
connected_machines = 0

# Variables for experiments
# list of id and late amount in a pair [(0, 0.2), (1, 5.3)...]
to_be_completed: int = 0
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
        machines.remove_socket(websocket)
        logger.log_message(f'Device disconnected, new amount: {len(machines)}')


async def establish_server():
    global machines
    """Start a websocket server on ws://192.168.1.10:5001, upon a new connection call new_connection while the server runs handle_server."""
    host = '192.168.1.10'
    port = 5001
    async with websockets.serve(new_connection, host, port, max_size=None) as websocket:
        machines.any_connection = Future()
        await handle_server()


async def handle_server():
    """Has the server "run in the background" for task offloading to the machines connected."""
    await sleep(0.1)
    recievers_up = False
    while True:
        await sleep(0.01)
        if not machines.empty() and not recievers_up:
            create_task(aggregate_recievers())
            recievers_up = True
        # If there is a task and a machine then start a new task by splitting a matrix into vector pairs
        if len(task_queue) != 0 and not machines.empty():
            tasks = [create_task(task_handler()) for _ in task_queue]
            await wait(tasks)
        if len(task_queue) == 0 and completed_tasks > 0 and completed_tasks == to_be_completed:
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
    # Handle the contiuous check of available machines here or earlier
    await machines.any_connection
    if task.get('offloading_parameters').get("offloading_type") == "Auction":
        await auction_call(task, machines)


def handle_client_input():
    '''
    Generate tasks depending on input from the frontend and add them to the queue.\n
    Sends the requested tasks in batches to handle task frequency (1/sec, 5/sec...) and waits if the batch hasn't taken 1 second yet.
    '''
    global connected_machines, start_client_timer, to_be_completed
    while True:
        if len(client_inputs) > 0:
            start_client_timer = time.time()
            connected_machines = len(machines)
            client_input = client_inputs.popleft()
            amount = client_input.get('amount')
            to_be_completed += amount
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
    global completed_tasks, start_machine_timer, start_fog_timer, start_client_timer, late_tasks
    logger.log_colored_message(
        logger.colors.GREEN, f'Number of tasks: {completed_tasks}')
    logger.log_colored_message(logger.colors.GREEN,
                               f'Fog Throughput: {completed_tasks / (time.time() - start_fog_timer)}')
    logger.log_colored_message(logger.colors.GREEN,
                               f'Client Throughput: {completed_tasks / (time.time() - start_client_timer)}')
    logger.log_colored_message(logger.colors.GREEN,
                               f'Machine Throughput: {completed_tasks / (sum([result.get("time") for result in results])/len(results))}')
    logger.log_colored_message(logger.colors.GREEN,
                               f'late tasks: {len(late_tasks)/completed_tasks*100}%')
    logger.log_colored_message(logger.colors.GREEN,
                               f'Average of task delays: {sum([delay[1] for delay in late_tasks])/completed_tasks}')
    logger.log_colored_message(logger.colors.GREEN,
                               f'Maximum of task delays: {max([delay[1] for delay in late_tasks])}')
    logger.log_colored_message(
        logger.colors.GREEN, f'Clients connected: {connected_machines}')
    shutil.copyfile(
        'log.txt', f'logs/finished_log {datetime.today().isoformat(sep=" ", timespec="seconds")}.txt')
    completed_tasks = 0
    late_tasks = []
    start_fog_timer = time.time()
    logger.truncate()


async def websocket_receiver(websocket):
    global auctions, completed_tasks
    async for message in websocket:
        received = json.loads(message)
        if isinstance(received, dict):
            if received.get('bid'):  # Bid
                auction = auctions.get(received.get('task_id'))
                if auction.get('bid_results'):
                    auction.get('bid_results').append(received)
                else:
                    auction['bid_results'] = [received]

                if len(auction.get('machines')) == len(auction.get('bid_results')):
                    await handle_bid(auction)
            elif received.get('result'):  # Matrix result
                auction = auctions.get(received.get('task_id'))
                await auction_result(
                    received,
                    auction,
                    auction.get('offloading_parameters'))
                completed_tasks += 1


async def aggregate_recievers():
    while True:
        if len(machines) > 0: # possible not handling addition of machines
            await asyncio.gather(*[websocket_receiver(machine[1]) for machine in machines])


async def receive_exception_handler(results):
    # For getting the ip out of a websocket for the failed recieves
    exceptions = [bool(f.exception()) for f in results]
    l = list()
    for i in range(len(results)):
        if not exceptions[i]:
            l.append(json.loads(list(results)
                                [i].result()).get('id'))
    mlist = machines.copy()
    for id, m in mlist.copy():
        for f in l:
            if id == f:
                mlist.remove((id, m))
    for m in mlist:
        logger.log_error(
            f'error on IP: {m[1].remote_address[0]}')


if __name__ == "__main__":
    try:
        logger.truncate()
        Thread(target=start_frontend, args=()).start()  # start flask server
        # handle client input in a seperate thread so frontend doesn't hang
        Thread(target=handle_client_input, args=()).start()
        uvloop.install()
        asyncio.run(establish_server())  # Run establish_server asynchronously
    except Exception as e:
        logger.log_error(f'General Error: {e}')
