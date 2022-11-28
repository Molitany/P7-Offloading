import json
import websockets
from asyncio import Lock, wait, create_task, wait_for
import random
from MachineQueue import MachineQueue

FPSB = 1
SPSB = 2
task_id = 0
auction_running = Lock()

async def auction_call(offloading_parameters, task, machines: MachineQueue):
    global task_id, auction_running
    #Universal part for all auctions
    offloading_parameters["task"] = task
    task_id += 1
    offloading_parameters["task_id"] = task_id
    offloading_parameters["max_reward"] = random.randrange(1, 11) #change reward calculation eventually
    
    await auction_running.acquire()
    try:
        await machines.any_connection
        for machine in machines.copy():
            await machine[1].send(json.dumps((machine[0], offloading_parameters))) #Broadcast the offloading parameters, including the task, to everyone with their respective ids

        receive_tasks = []
        websocketList = [w[1] for w in machines.copy()]
        for connection in websocketList:
            receive_tasks.append(create_task(connection.recv())) #Create a task to receive bids from every machine

        print(f'recv 1... machines: {machines}, task: {task_id}')
        finished, unfinished = await wait(receive_tasks, timeout=7) #Wait returns the finished and unfinished tasks in the list after the timeout

        received_values = []
        for finished_task in finished:
            received_values.append(json.loads(finished_task.result())) #Place the actual bids into the list
        auction_running.release()


        #Depending on the type of auction, call different functions
        if offloading_parameters.get('auction_type') == "SPSB" or offloading_parameters.get('auction_type') == "Second Price Sealed Bid":
            result = await sealed_bid(received_values, offloading_parameters, SPSB, machines)
            return result
        elif offloading_parameters.get('auction_type') == "FPSB" or offloading_parameters.get('auction_type') == "First Price Sealed Bid":
            result = await sealed_bid(received_values, offloading_parameters, FPSB, machines)
            return result
    except:
        auction_running.release()

async def sealed_bid(received_values, offloading_parameters, price_selector, machines: MachineQueue):
    sorted_values = sorted(received_values, key = lambda x:x["bid"])
    #broadcast actual reward to winner, and "you didnt win" to everone else
    #await response from winner

    if (len(sorted_values) > 1): #We should never run an auction with only 1 machine
        lowest_value, second_lowest = sorted_values[0], sorted_values[1]
        reward_value = sorted_values[1]['bid'] if price_selector == SPSB else sorted_values[0]['bid'] / 2
        non_winner_sockets = [machine[1] for machine in machines.copy() if machine[0] != lowest_value.get('id')]
        winner = None
        for machine in machines.copy():
            if machine[0] == lowest_value.get('id'):
                winner = machine
                machines.remove(winner)
                if len(non_winner_sockets) > 0:
                    websockets.broadcast(non_winner_sockets, json.dumps({"winner": False, 'task_id': offloading_parameters.get('task_id')}))
                await winner[1].send(json.dumps({"winner": True, "reward": reward_value, "task": offloading_parameters['task'], 'task_id': offloading_parameters['task_id']}))
                result = json.loads(await wait_for(winner[1].recv(), timeout=7))
                machines.put(winner)
                return result
    else:
        reward_value = sorted_values[0]['bid'] if price_selector == SPSB else sorted_values[0]['bid'] / 2
        if machines[0][0] == sorted_values[0].get('id'):
            winner = machines[0]
            machines.remove(winner)
            await winner[1].send(json.dumps({"winner": True, "reward": reward_value, "task": offloading_parameters['task'], 'task_id': offloading_parameters['task_id']}))
            result = json.loads(await wait_for(winner[1].recv(), timeout=7))
            machines.put(winner)
            return result
