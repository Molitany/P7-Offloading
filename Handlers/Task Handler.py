import os
import asyncio
import websockets


async def establish_client():
    host = '192.168.1.10'
    port = 5001
    async with websockets.connect(f"ws://{host}:{port}") as websocket:
        await websocket.send(os.popen(
            'ip addr show eth0 | grep "\<inet\>" | awk \'{ print $2 }\' | awk -F "/" \'{ print $1 }\'')
                             .read()
                             .strip()
                             .encode())
        print(await websocket.recv())
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(establish_client())
