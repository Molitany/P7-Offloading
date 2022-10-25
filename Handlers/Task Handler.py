import asyncio
import json_numpy

import websockets
import numpy as np


def calc_split_matrix(vector_pairs):
    dot_products = []
    for pair in vector_pairs:
        dot_products.append({"dot_product": np.dot(pair["vector"][0], pair["vector"][1]),
                             "cell": pair["cell"]})
    return dot_products


async def establish_client():
    host = '192.168.1.10'
    port = 5001
    async with websockets.connect(f"ws://{host}:{port}") as websocket:
        while True:
            task = json_numpy.loads(await websocket.recv())
            result = calc_split_matrix(task)
            await websocket.send(json_numpy.dumps(result))


if __name__ == "__main__":
    asyncio.run(establish_client())
