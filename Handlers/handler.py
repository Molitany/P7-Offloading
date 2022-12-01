import asyncio
import json
import traceback

from websockets import connect
import numpy as np
from websockets.exceptions import ConnectionClosed, InvalidMessage
import random
import time

CRED    = '\33[31m'
CGREEN  = '\33[32m'
CBLUE   = '\33[34m'
CGREENHIGH  = '\33[92m'
CBLUEHIGH   = '\33[94m'
CWHITE = '\33[97m'

internal_value = 0
idle_start_time = time.time()
IDLE_POWER_CONSUMPTION = 1
ACTIVE_POWER_CONSUMPTION = 5
task_difficulty_duration = {}
prev_task_id = -1

def calc_split_matrix(matrices):
    global task_difficulty_duration
    global internal_value
    active_start_time = time.time()

    """Dot products the pair into the respective cell."""
    matrix1 = matrices.get('mat1')
    matrix2 = matrices.get('mat2')
    result = np.matmul(matrix1, matrix2)

    # Dont do this but required to send as json instead of ndarray
    a: list = list()
    for i in range(len(result)):
        a.append(list(result[i]))

    task_duration = (time.time() - active_start_time)
    task_difficulty_duration['max_shape_number'] = task_duration

    internal_value -= task_duration
    return a


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
            async with connect(f"ws://{host}:{port}", max_size=None) as websocket:
                while True:
                    await recieve_handler(websocket)

        except ConnectionRefusedError:
            print(f'{CRED}Connection refused{CWHITE}')
            await asyncio.sleep(1)
        except ConnectionClosed:
            print(f'{CRED}Connection closed{CWHITE}')
            await asyncio.sleep(1)
        except asyncio.exceptions.TimeoutError:
            print(f'{CRED}Connection timed out{CWHITE}')
            await asyncio.sleep(1)
        except InvalidMessage:
            print(f'{CRED}Invalid Message{CWHITE}')
            await asyncio.sleep(1)
        except Exception:
            print(f'{CRED} Unknown Error{CWHITE}')
            traceback.print_exc()
            await asyncio.sleep(1)


async def recieve_handler(websocket):
    global prev_task_id
    received = json.loads(await websocket.recv())
    if isinstance(received, list):
        await auction_action(websocket, received)
    elif isinstance(received, dict):
        print(f'{CBLUEHIGH}finished receiving winner: {received["winner"]}{CWHITE}')
        if received.get('winner'):
            await winner_action(websocket, received)
        prev_task_id = received.get('task_id')

async def auction_action(websocket, recieved):
    id, offloading_parameters = recieved
    print(f'{CBLUEHIGH}finished receiving auction {{id:{id} task:{offloading_parameters.get("task_id")}}}{CWHITE}')
    if offloading_parameters["offloading_type"] == "Auction":
        if offloading_parameters["auction_type"] == "Second Price Sealed Bid" or offloading_parameters["auction_type"] == "SPSB" or offloading_parameters["auction_type"] == "FPSB" or offloading_parameters["auction_type"] == "First Price Sealed Bid":
            await bid_truthfully(offloading_parameters, websocket, id)

async def winner_action(websocket, auction_result):
    global internal_value, idle_start_time, prev_task_id
    result = calc_split_matrix(auction_result["task"]) #Interrupt here for continuous check for new auctions and cancelling current auction
        #The above maybe needs to be done in a separate process, so we can compute while still judging auctions
        #This does require far better estimation of whether auctions are worth joining
    print(f'{CGREEN}sending result...{CWHITE}')
    await websocket.send(json.dumps(result))
    print(f'{CGREENHIGH}finished sending result{CWHITE}')
    internal_value += auction_result["reward"]
    idle_start_time = time.time()
    prev_task_id = auction_result['task_id']

async def bid_truthfully(offloading_parameters, websocket, id):
    global idle_start_time
    global internal_value
    global task_difficulty_duration
    #We have the task as offloading_parameters["task"] for difficulty measuring
    # we have deadlines, the task, the frequency, the max reward, and fines

    internal_value = (idle_start_time - time.time()) * IDLE_POWER_CONSUMPTION
    idle_start_time = time.time()

    #Change the bid to be based on the dynamically estimated cost of the task
    #get previous time to complete, else estimate as 1ms per line in vector
    estimated_cost_of_task = task_difficulty_duration.get(offloading_parameters.get('task').get("max_shape_number"), offloading_parameters.get('task').get("max_shape_number") * 0.001) * IDLE_POWER_CONSUMPTION 
    if internal_value < 0:
        bid_value = estimated_cost_of_task + abs(internal_value)

    if offloading_parameters.get("deadlines") == True:
        if offloading_parameters.get('task').get("deadline_seconds") < estimated_cost_of_task:
            bid_value += offloading_parameters["task"].get("fine", 0) 

    print(f'{CGREEN}start sending {bid_value}:{id}...{CWHITE}')
    if offloading_parameters.get("max_reward") == True:
        if bid_value < offloading_parameters.get('task').get("max_reward"):
            await websocket.send(json.dumps({"bid": bid_value, 'id': id}))
        else:
            await websocket.send(json.dumps({"bid": offloading_parameters.get('task').get("max_reward"), 'id': id}))
    else:
        await websocket.send(json.dumps({"bid": bid_value, 'id': id}))
    print(f'{CGREENHIGH}finished sending{CWHITE}')
 


if __name__ == '__main__':
    asyncio.run(establish_client())
