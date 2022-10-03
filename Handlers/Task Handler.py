import socket
import asyncio
import websockets 

async def handler(websocket):
    async for task in websocket:
        print(task)

async def reverse_proxy(stop):
    async with websockets.serve(handler, socket.gethostbyname(socket.gethostname()), 5001):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(reverse_proxy())