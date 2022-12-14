import asyncio
import json
import traceback

from websockets import connect
import numpy as np
from websockets.exceptions import ConnectionClosed, InvalidMessage
from logger import Logger
import time


internal_value = 0
idle_start_time = time.time()
IDLE_POWER_CONSUMPTION = 1
ACTIVE_POWER_CONSUMPTION = 5
task_difficulty_duration = {}
prev_task_id = -1
logger = Logger()


def calc_split_matrix(matrices):
    global task_difficulty_duration
    global internal_value
    timer = time.time()

    """Dot products the pair into the respective cell."""
    result = matrices.get('mat1')
    matrix2 = matrices.get('mat2')
    for x in range(0, 100):
        result = np.matmul(result, matrix2)

    # Dont do this but required to send as json instead of ndarray
    a: list = list()
    for i in range(len(result)):
        a.append(list(result[i]))

    task_duration = (time.time() - timer)
    # Adds the task size to memory to give a better estimate for bidding later
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
            logger.log_error('Connection refused')
            await asyncio.sleep(1)
        except ConnectionClosed:
            logger.log_error('Connection closed')
            await asyncio.sleep(1)
        except asyncio.exceptions.TimeoutError:
            logger.log_error('Connection timed out')
            await asyncio.sleep(1)
        except InvalidMessage:
            logger.log_error('Invalid Message')
            await asyncio.sleep(1)
        except Exception:
            logger.log_error(f'Unknown Error: {traceback.print_exc()}')
            await asyncio.sleep(1)


async def recieve_handler(websocket):
    global prev_task_id
    received = json.loads(await websocket.recv())
    if isinstance(received, list):
        await auction_action(websocket, received)
    elif isinstance(received, dict):
        logger.log_colored_message(
            logger.colors.BLUEHIGH, f'finished receiving winner: {received["winner"]}')
        if received.get('winner'):
            await winner_action(websocket, received)
        prev_task_id = received.get('task_id')


async def auction_action(websocket, recieved):
    id, offloading_parameters = recieved
    logger.log_colored_message(
        logger.colors.BLUEHIGH, f'finished receiving auction {{id:{id} task:{offloading_parameters.get("task_id")}}}')
    if offloading_parameters["offloading_type"] == "Auction":
        if offloading_parameters["auction_type"] == "Second Price Sealed Bid" or offloading_parameters["auction_type"] == "SPSB" or offloading_parameters["auction_type"] == "FPSB" or offloading_parameters["auction_type"] == "First Price Sealed Bid":
            await bid_truthfully(offloading_parameters, websocket, id)


async def winner_action(websocket, auction_result: dict):
    global internal_value, idle_start_time, prev_task_id
    # Interrupt here for continuous check for new auctions and cancelling current auction
    result = calc_split_matrix(auction_result.get("task"))
    # The above maybe needs to be done in a separate process, so we can compute while still judging auctions
    # This does require far better estimation of whether auctions are worth joining
    logger.log_colored_message(logger.colors.GREEN, 'sending result...')
    await websocket.send(json.dumps({'result': result, 'task_id': auction_result.get('task_id')}))
    logger.log_colored_message(
        logger.colors.GREENHIGH, 'finished sending result')
    internal_value += auction_result.get("reward")
    idle_start_time = time.time()
    prev_task_id = auction_result.get('task_id')


async def bid_truthfully(offloading_parameters, websocket, id):
    global idle_start_time
    global internal_value
    global task_difficulty_duration
    # we have deadlines, the task, the frequency, the max reward, and fines
    internal_value = (idle_start_time - time.time()) * IDLE_POWER_CONSUMPTION
    idle_start_time = time.time()

    # Change the bid to be based on the dynamically estimated cost of the task
    # get previous time to complete, else estimate as 1ms per line in vector
    max_shape_num = offloading_parameters.get("max_shape_number")
    estimated_cost_of_task = task_difficulty_duration.get(
        max_shape_num, max_shape_num * 0.001) * IDLE_POWER_CONSUMPTION
    if internal_value < 0:
        bid_value = estimated_cost_of_task + \
            abs(internal_value)  # add the idle time to the bid

    if offloading_parameters.get("deadlines") == True:
        if offloading_parameters.get("deadline_seconds") < estimated_cost_of_task:
            # If the deadline is smaller than what is expected, add the fine to the bid to make a profit (if it exists).
            bid_value += offloading_parameters.get("fine", 0)

    to_send = {}
    if offloading_parameters.get("max_reward") == True:
        # get the maximum reward possible if the bid exceeds it
        if bid_value < offloading_parameters.get("max_reward"):
            to_send = {"bid": bid_value, 'id': id}
        else:
            to_send = {"bid": offloading_parameters.get(
                "max_reward"), 'id': id}
    else:
        to_send = {"bid": bid_value, 'id': id}
    to_send['task_id'] = offloading_parameters.get('task_id')
    logger.log_colored_message(
        logger.colors.GREEN, f'start sending {bid_value}:{id}...')
    await websocket.send(json.dumps(to_send))
    logger.log_colored_message(logger.colors.GREENHIGH, 'finished sending')


if __name__ == '__main__':
    asyncio.run(establish_client())
