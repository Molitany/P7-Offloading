import asyncio
import json

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

internal_value = 0
idle_start_time = time.time()
IDLE_POWER_CONSUMPTION = 1
ACTIVE_POWER_CONSUMPTION = 5
task_difficulty_duration = {}

def calc_split_matrix(matrices):
    global task_difficulty_duration
    global internal_value
    active_start_time = time.time()

    """Dot products the pair into the respective cell."""
    print(matrices)
    matrix1 = matrices.get('mat1')
    matrix2 = matrices.get('mat2')
    result = np.matmul(matrix1, matrix2)

    task_duration = (active_start_time - time.time())
    task_difficulty_duration['max_shape_number'] = task_duration

    internal_value -= task_duration
    return result


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
                    print(f'{CBLUE}start receiving auction...')
                    res = json.loads(await websocket.recv())
                    id, offloading_parameters = res
                    print(f'{CBLUEHIGH}finished receiving {id}:{offloading_parameters}')
                    if offloading_parameters["offloading_type"] == "Auction":
                        if offloading_parameters["auction_type"] == "Second Price Sealed Bid" or offloading_parameters["auction_type"] == "SPSB" or offloading_parameters["auction_type"] == "FPSB" or offloading_parameters["auction_type"] == "First Price Sealed Bid":
                            auction_result = await bid_truthfully(offloading_parameters, websocket, id)
                            print(f'{CBLUEHIGH}finished receiving {auction_result}')
                        if isinstance(auction_result, dict) and auction_result["winner"] == True:
                            result = calc_split_matrix(auction_result["task"]) #Interrupt here for continuous check for new auctions and cancelling current auction
                            #The above maybe needs to be done in a separate process, so we can compute while still judging auctions
                            #This does require far better estimation of whether auctions are worth joining
                            print(f'{CGREEN}sending result {result}')
                            await websocket.send(json.dumps(result))
                            print(f'{CGREENHIGH}finished sending result')
                            global internal_value
                            internal_value += auction_result["reward"]
                            global idle_start_time
                            idle_start_time = time.time()


        except ConnectionRefusedError:
            print(f'{CRED}Connection refused')
            await asyncio.sleep(1)
        except ConnectionClosed:
            print(f'{CRED}Connection closed')
            await asyncio.sleep(1)
        except asyncio.exceptions.TimeoutError:
            print(f'{CRED}Connection timed out')
            await asyncio.sleep(1)
        except InvalidMessage:
            print(f'{CRED}Invalid Message')
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass


async def bid_truthfully(offloading_parameters, websocket, id):
    global idle_start_time
    global internal_value
    global task_difficulty_duration
    #We have the task as offloading_parameters["task"] for difficulty measuring
    # we have deadlines, the task, the frequency, the max reward, and fines
    op = offloading_parameters

    internal_value = (idle_start_time - time.time()) * IDLE_POWER_CONSUMPTION
    idle_start_time = time.time()

    #Change the bid to be based on the dynamically estimated cost of the task
    #get previous time to complete, else estimate as 1ms per line in vector
    estimated_cost_of_task = task_difficulty_duration.get(op['task']['max_shape_number'] , op['task']['max_shape_number'] * 0.001) * IDLE_POWER_CONSUMPTION 
    if internal_value < 0:
        bid_value = estimated_cost_of_task + abs(internal_value)

    if op.get("deadlines") == "Yes":
        if op["task"].get("deadline") < task_difficulty_duration[op['task']['max_shape_number']]:
            bid_value += op["task"].get("fine", 0) 

    print(f'{CGREEN}start sending {bid_value}:{id}...')
    if op.get("map_reward") == "Yes":
        if bid_value < op["task"].get("max_reward"):
            await websocket.send(json.dumps({"bid": bid_value, 'id': id}))
        else:
            await websocket.send(json.dumps({"bid": op["max_reward"], 'id': id}))
    else:
        await websocket.send(json.dumps({"bid": bid_value, 'id': id}))
    print(f'{CGREENHIGH}finished sending')
    print(f'{CBLUE}start receiving result...')
    return json.loads(await websocket.recv())
 


if __name__ == '__main__':
    asyncio.run(establish_client())
