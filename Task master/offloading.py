from asyncio import sleep, run, wait_for, create_task, wait, FIRST_EXCEPTION
import asyncio
from asyncio.exceptions import TimeoutError as AsyncTimeoutError
from collections import deque
from flask import Flask, request
import websockets
import numpy as np
import json_numpy
from websockets.exceptions import ConnectionClosed

app = Flask(__name__)
machines_connected = deque()

matrix1 = np.array([[1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                    [10, 12, 14]])

matrix2 = np.array([[1, 2, 3, 10],
                    [4, 5, 6, 10],
                    [7, 8, 9, 10]])
# the task queue is a list of pairs where both elements are matrices
task_queue = deque([(matrix1, matrix2)])

def split_matrix(a, b):
    """
    Split the matrix into vector pairs and the specific cell to be multiplied into.
    """
    array_to_be_filled = np.zeros((np.shape(a)[0], np.shape(b)[1]))
    vector_pairs = []
    if np.shape(a)[1] == np.shape(b)[0]:
        for i in range(0, np.shape(a)[0]):
            for j in range(0, np.shape(b)[1]):
                vector_pairs.append({'vector': [a[i, :].tolist(), b[:, j].tolist()],
                                     'cell': [i, j]})
    else:
        print('illegal vector multiplication')
    return vector_pairs, array_to_be_filled


def fill_array(dot_products, array_to_be_filled):
    """
    Gathers the pairs back into a full matrix post multiplication.
    """
    for dot_product in dot_products:
        array_to_be_filled[dot_product['cell'][0]][dot_product['cell'][1]] = dot_product['dot_product']
    return array_to_be_filled.tolist()


async def new_connection(websocket):
    """
    Upon a new websocket connection add the machine to the known machines and set it to available\n
    when the connection is disrupted (Timeout, ConnectionClosed, etc.) the machine is removed from the known machines. 
    """
    machines_connected.append(websocket)
    try:
        await websocket.wait_closed()
    finally:
        machines_connected.remove(websocket)

async def machine_available():
    """
    Check the machines availability, if it is not available wait for the retry specified and check the availability again.
    If it suceeds then the function returns.
    """
    while not machines_connected:
        are_machines_available = asyncio.get_event_loop().create_future()
        try:
            await are_machines_available
        except:
            are_machines_available.cancel()
    return True


async def handle_communication(pair):
    """
    Send and recieve on an available machine through websockets.
    """
    while True:
        # Wait for a machine to be able to recieve order
        await machine_available()
        # mutex by taking machine from list of available machines
        machine = machines_connected.popleft()
        await machine.send(json_numpy.dumps(pair))
        result = json_numpy.loads(await machine.recv())
        machines_connected.append(machine)
        return result


async def handle_server():
    """
    Has the server "run in the background" for task offloading to the machines connected.
    """
    while True:
        await sleep(0.1)
        # If there is a task and a machine then start a new task by splitting a matrix into vector pairs
        if len(task_queue) != 0 and len(machines_connected) != 0:
            task = task_queue.popleft()
            vector_pairs, array_to_be_filled = split_matrix(task[0], task[1])
            # send vector pairs to machines. 
            results = await safe_send(vector_pairs)
            # Upon retrieval put the matrix back together and display the result.
            dot_product_array = fill_array(results, array_to_be_filled)
            print(f'we got: {dot_product_array}\n should be: {np.matmul(matrix1, matrix2)}\n'
                  f'equal: {dot_product_array == np.matmul(matrix1, matrix2)}')
            print(f'Clients: {len(machines_connected)}')
            task_queue.append((matrix1, matrix2))


async def safe_send(vector_pairs: list):
    """
    Split vector pairs and safely send the pairs to machines.
    """
    sub_tasks = {}
    results = []
    # Create tasks for all the pairs
    for pair in vector_pairs:
        sub_tasks.update({create_task(handle_communication(pair)): pair})
    while len(sub_tasks) != 0:
        try:
            # Run all of the tasks "at once" waiting for 5 seconds then it times out.
            # The wait stops when a task hits an exception or until they are all completed
            done, pending = await wait(sub_tasks.keys(), timeout=5, return_when=FIRST_EXCEPTION)
            for task in done:
                # ConnectionClosedOK is done but also an exception, so we have to check if the task is actually returned a result.
                if task.exception() is None:
                    results.append(task.result())
                    sub_tasks.pop(task)
        except (AsyncTimeoutError, ConnectionClosed) as e:
            pass
        finally:
            # if we are not done then we cancel all of the tasks, as they have been assigned to a machine already, 
            # and create the missing tasks again and try sending the missing pairs again. 
            if sub_tasks != 0:
                map(lambda sub_task: sub_task.cancel(), sub_tasks.keys())
                pairs = list(sub_tasks.copy().values())
                sub_tasks.clear()
                for pair in pairs:
                    sub_tasks.update({create_task(handle_communication(pair)): pair})
    return results


async def establish_server():
    """
    Start a websocket server on ws://192.168.1.10:5001, upon a new connection call new_connection while the server runs handle_server.
    """
    host = '192.168.1.10'
    port = 5001
    async with websockets.serve(new_connection, host, port) as websocket:
        await handle_server()


@app.route("/", methods=["POST"])
def receive_task():
    print(request.json)
    return 'ok'


if __name__ == "__main__":
    # Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    # Run establish_server asynchronously 
    run(establish_server())
