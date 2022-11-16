import json
import websockets
import asyncio
import random


async def sealed_bid(received_values, machines, task, price_selector):
    sorted_values = sorted(received_values, key = lambda x:x["bid"])
    #broadcast actual reward to winner, and "you didnt win" to everone else
    #await response from winner

    if (len(sorted_values) > 1): #We should never run an auction with only 1 machine
        lowest_value, second_lowest = sorted_values[0], sorted_values[1]
        reward_value = sorted_values[1]['bid'] if price_selector == 2 else sorted_values[0]['bid'] / 2
        non_winner_sockets = [machine[1] for machine in machines if machine[0] != lowest_value.get('id')]
        winner = None
        for machine in machines:
            if machine[0] == lowest_value.get('id'):
                winner = machine
                if len(non_winner_sockets) > 0:
                    websockets.broadcast(non_winner_sockets, json.dumps({"winner": False}))
                await winner[1].send(json.dumps({"winner": True, "reward": reward_value, "task": task}))
                return (winner, json.loads(await asyncio.wait_for(winner[1].recv(), timeout=3)))
    else:
        reward_value = sorted_values[0]['bid'] if price_selector == 2 else sorted_values[0]['bid'] / 2
        for machine in machines:
            if machine[0] == sorted_values[0].get('id'):
                winner = machine
                await winner[1].send(json.dumps({"winner": True, "reward": reward_value, "task": task}))
                return (winner, json.loads(await asyncio.wait_for(winner[1].recv(), timeout=3)))

#Reward is highest bid halved halved to make the FPSB incentive compatible
#This enforced a Bayesian Nash Equilibrium strategy
#Where the optimal choice is to be truthful
#This also makes the output very similar to SPSB, so we might wanna change it