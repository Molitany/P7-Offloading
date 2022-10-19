import os
import socket
import asyncio
import websockets


async def handler(websocket):
    try:
        async for task in websocket:
            print(task)
    except websockets.ConnectionClosed:
        print('connection terminated')


async def reverse_proxy():
    host = os.popen(
        'ip addr show eth0 | grep "\<inet\>" | awk \'{ print $2 }\' | awk -F "/" \'{ print $1 }\'').read().strip()
    port = 5001
    async with websockets.serve(handler, host, port):
        print(f"Server started on {host}:{port}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(reverse_proxy())
