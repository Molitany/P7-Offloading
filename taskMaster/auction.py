import json
import time
import websockets
from asyncio import Lock
from machineQueue import MachineQueue
from logger import Logger
from globals import late_tasks, auctions, results, machines


logger = Logger()
task_id = 0
auction_running = Lock()
start_machine_timer: float = 0
lock = Lock()
machines_list = []


async def auction_call(task: dict, machines: MachineQueue):
    '''
    Starts an auction with the giving parameters for the task given.\n
    First sending a notice of the new auction and then waiting for the returning bids.\n
    Then find the winning machine based on the auction type.\n
    Returning the result of the task that has been offloaded.
    '''
    global task_id, auction_running, start_delay_timer, start_machine_timer, machines_list, auctions
    # Universal part for all auctions
    offloading_parameters: dict  = task.pop('offloading_parameters')
    offloading_parameters['max_shape_number'] = task.get('max_shape_number')

    # Use a lock to ensure only one auction is running since we cannot recv twice on the same machine
    try:
        await machines.any_connection
        machines_list = machines
        start_delay_timer = time.time()
        start_machine_timer = time.time()
        task_id += 1
        offloading_parameters["task_id"] = task_id

        connections = machines.connected
        for machine in connections.copy():
            # Broadcast the offloading parameters, including the task, to everyone with their respective ids
            await machine[1].send(json.dumps((machine[0], offloading_parameters)))
        auctions[task_id] = {
            'machines': connections, 
            'offloading_parameters': offloading_parameters.copy(),
            'task': task, 
            'bid_results': [], 
            'start_delay_timer': start_delay_timer, 
            'start_machine_timer': start_machine_timer}
    except:
        task['offloading_parameters'] = offloading_parameters


async def handle_bid(auction):
    # Depending on the type of auction, call different functions
    results = auction.get('bid_results')
    offloading_parameters = auction.get('offloading_parameters')
    task = auction.get('task')
    task_id = offloading_parameters.get('task_id')
    machines = auction.get('machines')

    result = None
    if offloading_parameters.get('auction_type') == 'SPSB':
        result = await _sealed_bid(results, task, task_id, 'SPSB', machines, auction)
    elif offloading_parameters.get('auction_type') == 'FPSB':
        result = await _sealed_bid(results, task, task_id, 'FPSB', machines, auction)
    return result


async def _sealed_bid(received_values, task, task_id, price_selector, machines, auction):
    '''
    Handles the sorting of bids, the resulting winner based on auction type.\n
    Sends out the result to the machines and the winner gets the task and is removed from the list of available machines.\n
    The winner is added back when it returns the result of the task.
    '''
    sorted_values = sorted(received_values, key=lambda x: x["bid"])
    # broadcast actual reward to winner, and "you didnt win" to everone else
    # await response from winner

    # We should never run an auction with only 1 machine...
    winner = None
    if (len(sorted_values) > 1):
        reward_value = sorted_values[1]['bid'] if price_selector == 'SPSB' else sorted_values[0]['bid'] / 2
        non_winner_sockets = [machine[1] for machine in machines.copy(
        ) if machine[0] != sorted_values[0].get('id')]
        for machine in machines.copy():
            if machine[0] == sorted_values[0].get('id'):
                winner = machine
                if len(non_winner_sockets) > 0:
                    websockets.broadcast(non_winner_sockets, json.dumps(
                        {"winner": False, 'task_id': task_id}))
    else:  # But if it happens then the only machine available wins
        reward_value = sorted_values[0]['bid'] if price_selector == 'SPSB' else sorted_values[0]['bid'] / 2
        if machines[0][0] == sorted_values[0].get('id'):
            winner = machines[0]
    await winner[1].send(json.dumps({"winner": True,
                                    "reward": reward_value,
                                     "task": task,
                                     'task_id': task_id}))
    auction['winner'] = winner


async def auction_result(result, auction, offloading_parameters):
    global results
    time_taken = time.time() - auction.get('start_delay_timer')
    if offloading_parameters.get('deadline_seconds') <= time_taken:
        late_tasks.append(
            (task_id, time_taken - offloading_parameters.get('deadline_seconds')))
    results.append({'time': time.time() - auction.get('start_machine_timer'), 'result': result})
