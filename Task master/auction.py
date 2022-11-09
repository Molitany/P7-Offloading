import json
import websockets
import asyncio
import random

async def auction_call(offloading_parameters, task, machines_connected):

    #Universal part for all auctions
    offloading_parameters["task"] = task
    offloading_parameters["max_reward"] = random.randrange(1, 11) #change reward calculation eventually
    if offloading_parameters.get("Fines") == "Yes": 
        offloading_parameters["fines"] = random.randrange(1, 6) #change fine calculation too
    

    websocketList = [m for m in machines_connected._queue]
    websockets.broadcast(websocketList, json.dumps(offloading_parameters)) #Broadcast the offloading parameters, including the task, to everyone

    receive_tasks = []
    for connection in websocketList:
        receive_tasks.append(asyncio.create_task(connection.recv())) #Create a task to receive bids from every machine

    finished, unfinished = await asyncio.wait(receive_tasks, timeout=3) #Wait returns the finished and unfinished tasks in the list after the timeout

    received_values = []
    for finished_task in finished:
        received_values.append(json.load(finished_task.result())) #Place the actual bids into the list

    #Depending on the type of auction, call different functions
    if offloading_parameters["Auction_type"] == "SPSB" or offloading_parameters["Auction_type"] == "Second Price Sealed Bid":
        await second_price_sealed_bid(received_values, offloading_parameters, task, machines_connected)


async def second_price_sealed_bid(received_values, offloading_parameters, task, machines_connected):

    sorted_values = sorted(received_values, key = lambda x:x["bid"])
    #broadcast actual reward to winner, and "you didnt win" to everone else
    #await response from winner

    lowest_value, second_lowest = sorted_values[0], sorted_values[1]

    non_winners = [m for m in machines_connected._queue if m != lowest_value]
    non_winner_sockets = [m for m in non_winners]
    await websockets.broadcast(non_winner_sockets, json.dumbs({"winner": False}))
    await websockets.send(lowest_value["socket"], json.dumbs({"winner": True, "reward": second_lowest["bid"], "task": task}))

    computation_result = await asyncio.wait_for(lowest_value["socket"].recv(), timeout=10)

    return computation_result
    