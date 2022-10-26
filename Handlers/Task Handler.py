import asyncio
import json_numpy

from websockets import connect
import numpy as np
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK


def calc_split_matrix(pair):
    print(pair)
    dot_products = {"dot_product": np.dot(pair["vector"][0], pair["vector"][1]),
                    "cell": pair["cell"]}
    return dot_products


async def establish_client():
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
        except (ConnectionClosedError, ConnectionClosedOK):
            print('Connection closed')

if __name__ == "__main__":
    asyncio.run(establish_client())
