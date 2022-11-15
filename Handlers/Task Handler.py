import asyncio
import json_numpy

from websockets import connect
import numpy as np
from websockets.exceptions import ConnectionClosed, InvalidMessage
import random
import time

internal_value = 0
idle_start_time = time.time()
IDLE_POWER_CONSUMPTION = 1
ACTIVE_POWER_CONSUMPTION = 5
task_difficulty_duration = {}

def calc_split_matrix(pair):
    global task_difficulty_duration
    global internal_value
    active_start_time = time.time()

    """Dot products the pair into the respective cell."""
    print(pair)
    dot_products = {"dot_product": np.dot(pair["vector"][0], pair["vector"][1]),
                    "cell": pair["cell"], "completed": True}

    task_duration = (active_start_time - time.time())
    task_difficulty_duration[len(pair["vector"])] = task_duration

    internal_value -= task_duration
    return dot_products


async def establish_client():
    """
    Starts the client and connects to the server on ws://192.168.1.10:5001.
    If the client fails then it will retry until the server is available again.

    Once connected wait for a task and execute it, sending the result back.
    """
    host = '192.168.1.10'
    port = 5001


    while True:
        try:
            async with connect(f"ws://{host}:{port}") as websocket:
                while True:

                    id, offloading_parameters = json_numpy.loads(await websocket.recv())
                    if offloading_parameters["offloading_type"] == "Auction":
                        if offloading_parameters["auction_type"] == "Second Price Sealed Bid" or offloading_parameters["auction_type"] == "SPSB":
                            auction_result = await bid_on_SPSB(offloading_parameters, websocket, id)
                    
                        if auction_result["winner"] == True:
                            result = calc_split_matrix(auction_result["task"]) #Interrupt here for continuous check for new auctions and cancelling current auction
                            #The above maybe needs to be done in a separate process, so we can compute while still judging auctions
                            #This does require far better estimation of whether auctions are worth joining
                            if result["completed"] == True:
                                await websocket.send(json_numpy.dumps(result))
                                global internal_value
                                internal_value += auction_result["reward"]
                                global idle_start_time
                                idle_start_time = time.time()


        except ConnectionRefusedError:
            print('Connection refused')
            await asyncio.sleep(1)
        except ConnectionClosed:
            print('Connection closed')
            await asyncio.sleep(1)
        except asyncio.exceptions.TimeoutError:
            print('Connection timed out')
            await asyncio.sleep(1)
        except InvalidMessage:
            print('Invalid Message')
            await asyncio.sleep(1)


async def bid_on_SPSB(offloading_parameters, websocket, id):
    global idle_start_time
    global internal_value
    global task_difficulty_duration
    #We have the task as offloading_parameters["task"] for difficulty measuring
    # we have deadlines, the task, the frequency, the max reward, and fines
    op = offloading_parameters

    internal_value = (idle_start_time - time.time()) * IDLE_POWER_CONSUMPTION
    idle_start_time = time.time()

    #Change the bid to be based on the dynamically estimated cost of the task
    estimated_cost_of_task = task_difficulty_duration.get(len(op["task"]["vector"]), len(op["task"]["vector"]) * 0.001) * IDLE_POWER_CONSUMPTION #get previous time to complete, else estimate as 1ms per line in vector
    if internal_value < 0:
        bid_value = estimated_cost_of_task + abs(internal_value)

    if op.get("deadlines") == "Yes":
        if op["task"].get("deadline") < task_difficulty_duration[len(op["task"]["vector"])]:
            bid_value += op["task"].get("fine", 0) 

    if op.get("map_reward") == "Yes":
        if bid_value < op["task"].get("max_reward"):
            await websocket.send(json_numpy.dumps({"bid": bid_value, 'id': id}))
        else:
            await websocket.send(json_numpy.dumps({"bid": op["max_reward"], 'id': id}))

    return json_numpy.loads(await websocket.recv())

    
if __name__ == '__main__':
    asyncio.run(establish_client())
