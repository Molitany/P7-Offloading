import asyncio
from websockets.legacy.server import WebSocketServerProtocol
from collections import deque

class MachineQueue():
    def __init__(self) -> None:
        self.connected: deque[tuple[int,WebSocketServerProtocol]] = deque()
        self.any_connection = asyncio.Future()
        self.id = 0
    
    def remove(self, element) -> None:
        self.connected.remove(element)
        if self.any_connection.done() and not self.connected:
            self.any_connection = asyncio.Future()
    
    def remove_socket(self,websocket) -> None:
        for machine in self.connected.copy():
            if machine[1] == websocket:
                self.remove(machine)

    def put(self, element) -> None:
        if (isinstance(element, tuple)):
            self.connected.append(element)
        else:
            self.connected.append((self.id, element))
            self.id += 1

        amount_elements = len(self.connected)
        if amount_elements > 0 and not self.any_connection.done():
            self.any_connection.set_result(None)

    def empty(self) -> bool:
        return not self.connected

    def copy(self):
        return self.connected.copy()

    def __iter__(self):
        return self.connected.__iter__()

    def __len__(self):
        return self.connected.__len__()

    def __str__(self) -> str:
        return self.connected.__str__()

    def __getitem__(self, item):
        return self.connected[item]
