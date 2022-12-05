from enum import Enum
import json
import time
import traceback
import websockets
from asyncio import Lock, wait, create_task
from machineQueue import MachineQueue
from logger import Logger
from globals import late_tasks


logger = Logger()
task_id = 0
auction_running = Lock()
start_delay_timer: float = 0
start_machine_timer: float = 0

async def auction_call(task: dict, machines: MachineQueue):
    '''
    Starts an auction with the giving parameters for the task given.\n
    First sending a notice of the new auction and then waiting for the returning bids.\n
    Then find the winning machine based on the auction type.\n
    Returning the result of the task that has been offloaded.
    '''
    global task_id, auction_running, start_delay_timer, start_machine_timer
    # Universal part for all auctions
    offloading_parameters = task.pop('offloading_parameters')
    offloading_parameters['max_shape_number'] = task.get('max_shape_number')

    # Use a lock to ensure only one auction is running since we cannot recv twice on the same machine
    await auction_running.acquire()
    try:
        await machines.any_connection
        start_delay_timer = time.time()
        start_machine_timer = time.time()
        task_id += 1
        offloading_parameters["task_id"] = task_id

        connections = machines.connected
        for machine in connections.copy():
            # Broadcast the offloading parameters, including the task, to everyone with their respective ids
            await machine[1].send(json.dumps((machine[0], offloading_parameters)))

        receive_tasks = []
        for connection in [c[1] for c in connections.copy()]:
            # Create a task to receive bids from every machine
            receive_tasks.append(create_task(connection.recv()))

        print(f'recv machines: {len(machines)}, task: {task_id}')
        # Wait returns the finished and unfinished tasks in the list after the timeout
        finished, unfinished = await wait(receive_tasks, timeout=7)

        received_values = []
        for finished_task in finished:
            if not finished_task.exception():  # Dont take the ones that failed
                # Place the actual bids into the list
                received_values.append(json.loads(finished_task.result()))
            else:
                # For getting the ip out of a websocket for the failed recieves
                exceptions = [bool(f.exception()) for f in finished]
                l = list()
                for i in range(len(finished)):
                    if not exceptions[i]:
                        l.append(json.loads(list(finished)
                                 [i].result()).get('id'))
                mlist = connections.copy()
                for id, m in mlist.copy():
                    for f in l:
                        if id == f:
                            mlist.remove((id, m))
                for m in mlist:
                    logger.log_error(
                        f'error on IP: {m[1].remote_address[0]}')

        auction_running.release()  # Release the lock as the auction part is over

        if received_values:
            # Depending on the type of auction, call different functions
            if offloading_parameters.get('auction_type') == 'SPSB':
                result = await _sealed_bid(received_values, task, offloading_parameters, task_id, 'SPSB', machines)
                return result
            elif offloading_parameters.get('auction_type') == 'FPSB':
                result = await _sealed_bid(received_values, task, offloading_parameters, task_id, 'FPSB', machines)
                return result
    except:
        task['offloading_parameters'] = offloading_parameters
        if auction_running.locked():
            auction_running.release()


async def _sealed_bid(received_values, task, offloading_parameters, task_id, price_selector, machines: MachineQueue):
    '''
    Handles the sorting of bids, the resulting winner based on auction type.\n
    Sends out the result to the machines and the winner gets the task and is removed from the list of available machines.\n
    The winner is added back when it returns the result of the task.
    '''
    sorted_values = sorted(received_values, key=lambda x: x["bid"])
    # broadcast actual reward to winner, and "you didnt win" to everone else
    # await response from winner

    # We should never run an auction with only 1 machine...
    result = None
    winner = None
    if (len(sorted_values) > 1):
        lowest_value, second_lowest = sorted_values[0], sorted_values[1]
        reward_value = sorted_values[1]['bid'] if price_selector == 'SPSB' else sorted_values[0]['bid'] / 2
        non_winner_sockets = [machine[1] for machine in machines.copy(
        ) if machine[0] != lowest_value.get('id')]
        for machine in machines.copy():
            if machine[0] == lowest_value.get('id'):
                winner = machine
                machines.remove(winner)
                if len(non_winner_sockets) > 0:
                    websockets.broadcast(non_winner_sockets, json.dumps(
                        {"winner": False, 'task_id': task_id}))
    else:  # But if it happens then the only machine available wins
        reward_value = sorted_values[0]['bid'] if price_selector == 'SPSB' else sorted_values[0]['bid'] / 2
        if machines[0][0] == sorted_values[0].get('id'):
            winner = machines[0]
            machines.remove(winner)

    await winner[1].send(json.dumps({"winner": True,
                                    "reward": reward_value,
                                     "task": task,
                                     'task_id': task_id}))
    result = json.loads(await winner[1].recv())
    machines.put(winner)    
    time_taken = time.time() - start_delay_timer
    if offloading_parameters.get('deadline_seconds') <= time_taken:
        late_tasks.append((task_id, time_taken - offloading_parameters.get('deadline_seconds')))
    return start_machine_timer, result
