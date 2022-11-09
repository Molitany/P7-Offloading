import asyncio
import json_numpy

from websockets import connect
import numpy as np
from websockets.exceptions import ConnectionClosed


def calc_split_matrix(pair):
    """Dot products the pair into the respective cell."""
    print(pair)
    dot_products = {"dot_product": np.dot(pair["vector"][0], pair["vector"][1]),
                    "cell": pair["cell"]}
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
                    task = json_numpy.loads(await websocket.recv())
                    result = calc_split_matrix(task)
                    await websocket.send(json_numpy.dumps(result))
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
