import asyncio
import json_numpy

from websockets import connect
import numpy as np
from websockets.exceptions import ConnectionClosed
import random



def calc_split_matrix(pair):
    """Dot products the pair into the respective cell."""
    print(pair)
    dot_products = {"dot_product": np.dot(pair["vector"][0], pair["vector"][1]),
                    "cell": pair["cell"], "completed": True}
    return dot_products


async def establish_client():
    """
    Starts the client and connects to the server on ws://192.168.1.10:5001.
    If the client fails then it will retry until the server is available again.

    Once connected wait for a task and execute it, sending the result back.
    """
    host = '192.168.1.10'
    port = 5001
    internal_value = 0

    while True:
        try:
            async with connect(f"ws://{host}:{port}") as websocket:
                while True:

                    offloading_parameters = json_numpy.loads(await websocket.recv())
                    if offloading_parameters["offloading_type"] == "Auction":
                        if offloading_parameters["auction_type"] == "Second Price Sealed Bid" or offloading_parameters["auction_type"] == "SPSB":
                            auction_result = bid_on_SPSB(offloading_parameters, websocket)
                    
                        if auction_result["winner"] == True:
                            result = calc_split_matrix(auction_result["task"]) #Interrupt here for continuous check for new auctions and cancelling current auction
                            #The above maybe needs to be done in a separate process, so we can compute while still judging auctions
                            #This does require far better estimation of whether auctions are worth joining
                            if result["completed"] == True:
                                await websocket.send(json_numpy.dumps(result))
                                internal_value += auction_result["reward"]

        except ConnectionRefusedError:
            print('no connection to server')
            await asyncio.sleep(1)
        except ConnectionClosed:
            print('Connection closed')
            await asyncio.sleep(1)
        except asyncio.exceptions.TimeoutError:
            print('Connection timed out')
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(establish_client())

async def bid_on_SPSB(offloading_parameters, websocket):
    #We have the task as offloading_parameters["task"] for difficulty measuring

    # we have deadlines, the task, the frequency, the max reward, and fines
    op = offloading_parameters

    if len(op["task"]["vector"]) < op["max_reward"]:
        websocket.send(json_numpy.dumps({"bid": op["max_reward"] - random.randrange(1, 4)}))

    return json_numpy.loads(await websocket.recv())

    
