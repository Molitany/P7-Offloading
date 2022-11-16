import json
import websockets
import asyncio
import random


async def second_price_sealed_bid(received_values, machine, task, machines_connected):
    sorted_values = sorted(received_values, key = lambda x:x["bid"])
    #broadcast actual reward to winner, and "you didnt win" to everone else
    #await response from winner

    if (len(sorted_values) > 1):
        lowest_value, second_lowest = sorted_values[0], sorted_values[1]

        non_winner_sockets = [machine[1] for machine in machines_connected if machine[0] != lowest_value.get('id')]
        winner = None
        for machine in machines_connected:
            if machine[0] == lowest_value.get('id'):
                winner = machine
                if len(non_winner_sockets) > 0:
                    websockets.broadcast(non_winner_sockets, json.dumps({"winner": False}))
                await winner[1].send(json.dumps({"winner": True, "reward": second_lowest["bid"], "task": task}))
                return (winner, json.loads(await asyncio.wait_for(winner[1].recv(), timeout=3)))
    else:
        for machine in machines_connected:
            if machine[0] == sorted_values[0].get('id'):
                winner = machine
                await winner[1].send(json.dumps({"winner": True, "reward": sorted_values[0]['bid'], "task": task}))
                return (winner, json.loads(await asyncio.wait_for(winner[1].recv(), timeout=3)))
