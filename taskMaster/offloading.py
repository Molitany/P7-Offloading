from asyncio import sleep, run, wait, create_task
from collections import deque
from flask import Flask, request
import websockets
import numpy as np
import traceback
from MatrixGenerator import generate_matrices
from auction import auction_call
from MachineQueue import MachineQueue

app = Flask(__name__)
machines: MachineQueue
# the task queue is a list of pairs where both elements are matrices
task_queue = deque(generate_matrices(amount=2, min_mat_shape=100, max_mat_shape=100, fixed_seed=False))
prev_winner = None

def split_matrix(a, b):
    """Split the matrix into vector pairs and the specific cell to be multiplied into."""
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
    """Gathers the pairs back into a full matrix post multiplication."""
    for dot_product in dot_products:
        array_to_be_filled[dot_product['cell'][0]][dot_product['cell'][1]] = dot_product['dot_product']
    return array_to_be_filled.tolist()

#Do auction with all machines, its their job to respond or not
    #Machines should always be ready to respond and decline
    #Publish task, and receive calculated offers
    #Calculate second lowest offer using equation, and publish the winner ID to everyone
    #Send reward to winner
    #Send task to winner
    #Receive completed task


async def get_offloading_parameters():

    offloading_parameters = {}

    print("""What type of offloading to use?
    Auction (default) 
    Contract (not implemented)
    First come, first server (FCFS) (not implemented)\n""") #We could just define our 4 types here, normal, with fines, with max_reward, both and save some enter
    offloading_parameters["offloading_type"] = "Auction"

    if offloading_parameters["offloading_type"] == "Auction" or offloading_parameters["offloading_type"] == "auction":
        print("""What auction type to use?
        Second Price Sealed Bid (SPSB) (default)
        First Price Sealed Bid (FPSB)\n""")
        offloading_parameters["auction_type"] = "SPSB" #input() or "SPSB"

    print("""What frequency of tasks?
    Slow (1/s)
    Medium (5/s) (default)
    Fast (10/s)\n""")
    offloading_parameters["task_frequency"] = "Medium" #input() or "Medium"

    print("""Do the tasks have deadlines?
    No (Default)
    Yes \n""")
    offloading_parameters["deadlines"] = "No" #input() or "No"

    print("""Are there fines for abandoning a job or going over a possible deadline?
    No (default)
    Yes \n""")
    offloading_parameters["fines"] = "No" #input() or "No"

    print("""Is there a max reward for the tasks?
    No (Default) 
    Yes \n""")
    offloading_parameters["max_reward"] = "No" #input() or "No"

    #Simply add more cases to each of these or more categories
    #Handling of types is later and on the machines
    #Stuff likes this can also be split into seperate functions or its own file if needed

    return offloading_parameters


async def new_connection(websocket):
    """
    Upon a new websocket connection add the machine to the known machines and set it to available\n
    when the connection is disrupted (Timeout, ConnectionClosed, etc.) the machine is removed from the known machines. 
    """
    global machines
    machines.put(websocket)
    try:
        await websocket.wait_closed()
    finally:
        machines.remove_socket(websocket)


async def handle_communication(task, offloading_parameters):
    #Handle the contiuous check of available machines here or earlier
    #This stuff also need to be done concurrently for every single task that comes in
    await machines.any_connection
    if offloading_parameters["offloading_type"] == "Auction":
        return await auction_call(offloading_parameters, task, machines)


async def handle_server():
    """Has the server "run in the background" for task offloading to the machines connected."""
    global task_queue
    await sleep(0.1)
    while True:
        await sleep(0.01)
        # If there is a task and a machine then start a new task by splitting a matrix into vector pairs
        if len(task_queue) != 0 and not machines.empty():
            tasks = [create_task(task_handler()) for _ in machines]
            done, pending = await wait(tasks)
            task_queue = deque(generate_matrices(amount=7, min_mat_shape=300, max_mat_shape=300, fixed_seed=False))


async def task_handler():
    global task_queue
    task = task_queue.popleft()
    # vector_pairs, array_to_be_filled = split_matrix(task[0], task[1])
    # send vector pairs to machines. 

    results = await safe_send(task)
    # Upon retrieval put the matrix back together and display the result.
    # dot_product_array = fill_array(results, array_to_be_filled)
    print(f'equal: {results == np.matmul(task["mat1"], task["mat2"])}')
    print(f'Clients: {len(machines)}')


async def safe_send(task):
    """Split vector pairs and safely send the pairs to machines."""
    results = []
    #Potentially wrap this in a block that does a certain amount of tasks or has a certain duration, for easier experiment simulation
    offloading_parameters = await get_offloading_parameters()
    # Create tasks for all the pairs
    while True:
        try:
            return await handle_communication(task, offloading_parameters)
        except Exception:
            traceback.print_exc()


async def establish_server():
    global machines
    """Start a websocket server on ws://192.168.1.10:5001, upon a new connection call new_connection while the server runs handle_server."""
    host = '192.168.1.10'
    port = 5001
    async with websockets.serve(new_connection, host, port, max_size=None) as websocket:
        machines = MachineQueue()
        await handle_server()


@app.route("/", methods=["POST"])
def receive_task():
    print(request.json)
    return 'ok'


if __name__ == "__main__":
    # Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    # Run establish_server asynchronously 
    run(establish_server())
