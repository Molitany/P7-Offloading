import socket
import asyncio
import websockets 

async def handler(websocket):
    async for task in websocket:
        print(task)

async def reverse_proxy():
    host = socket.gethostbyname(socket.gethostname())
    port = 5001
    async with websockets.serve(handler, host, port):
        print(f"Server started on {host}:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(reverse_proxy())