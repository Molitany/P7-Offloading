import json
import websockets
import asyncio
import random

async def auction_call(offloading_parameters, task, machines_connected, auction_running: asyncio.Future):
    #Universal part for all auctions
    offloading_parameters["task"] = task
    offloading_parameters["max_reward"] = random.randrange(1, 11) #change reward calculation eventually
    
    machines = machines_connected
    websocketList = [w[1] for w in machines]
    for machine in machines:
        await machine[1].send(json.dumps((machine[0], offloading_parameters))) #Broadcast the offloading parameters, including the task, to everyone with their respective ids

    receive_tasks = []
    for connection in websocketList:
        receive_tasks.append(asyncio.create_task(connection.recv())) #Create a task to receive bids from every machine
        
    print(f'recv 1: websockets {websocketList}')
    finished, unfinished = await asyncio.wait(receive_tasks, timeout=3) #Wait returns the finished and unfinished tasks in the list after the timeout

    auction_running.get_loop().call_soon_threadsafe(auction_running.set_result, False)

    received_values = []
    for finished_task in finished:
        received_values.append(json.loads(finished_task.result())) #Place the actual bids into the list

    #Depending on the type of auction, call different functions
    if offloading_parameters.get('auction_type') == "SPSB" or offloading_parameters.get('auction_type') == "Second Price Sealed Bid":
        return await second_price_sealed_bid(received_values, machine, task, machines_connected)


async def second_price_sealed_bid(received_values, machine, task, machines_connected):
    sorted_values = sorted(received_values, key = lambda x:x["bid"])
    #broadcast actual reward to winner, and "you didnt win" to everone else
    #await response from winner

    if len(sorted_values) > 1:
        lowest_value, second_lowest = sorted_values[0], sorted_values[1]
    else:
        lowest_value, second_lowest = sorted_values[0], sorted_values[0]

    machines = machines_connected
    non_winner_sockets = [machine[1] for machine in machines if machine[0] != lowest_value.get('id')]
    winner = None
    for machine in machines:
        if machine[0] == lowest_value.get('id'):
            winner = machine

    if len(non_winner_sockets) > 1:
        await websockets.broadcast(non_winner_sockets, json.dumps({"winner": False}))
    await winner[1].send(json.dumps({"winner": True, "reward": second_lowest["bid"], "task": task}))
    computation_result = json.loads(await asyncio.wait_for(winner[1].recv(), timeout=3))
    return computation_result