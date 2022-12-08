import asyncio
from websockets.legacy.server import WebSocketServerProtocol
from collections import deque


class MachineQueue():
    '''A class to handle the state space of the queue.'''

    def __init__(self) -> None:
        self.connected: deque[tuple[int, WebSocketServerProtocol]] = deque()
        self.any_connection = None
        self.id = 0

    def remove(self, element) -> None:
        '''Removes an element from the queue and if it is now empty set any_connection to a new future for locking.'''
        if element in self.connected:
            self.connected.remove(element)
            if self.any_connection.done() and not self.connected:
                self.any_connection = asyncio.Future()

    def remove_socket(self, websocket) -> None:
        '''Removes an element from the queue based on a websocket'''
        for machine in self.connected.copy():
            if machine[1] == websocket:
                self.remove(machine)

    def put(self, element) -> None:
        '''adds an element to the queue regardless of websocket or (id,websocket) and sets the future if it is non empty.'''
        if (isinstance(element, tuple)):
            self.connected.append(element)
        else:
            self.connected.append((self.id, element))
            self.id += 1

        amount_elements = len(self.connected)
        if amount_elements > 0 and not self.any_connection.done():
            self.any_connection.set_result(None)

    def empty(self) -> bool:
        '''Returns if a bool for if the queue is empty.'''
        return not self.connected

    def copy(self) -> deque[tuple[int, WebSocketServerProtocol]]:
        '''Returns a copy of the queue.'''
        return self.connected.copy()

    def __iter__(self):
        '''Returns an iterable object to go through elements in the queue.'''
        return self.connected.__iter__()

    def __len__(self):
        '''returns the length of the queue.'''
        return self.connected.__len__()

    def __str__(self) -> str:
        '''Stringify the queue.'''
        return self.connected.__str__()

    def __getitem__(self, item):
        '''Get a specific element in the queue.'''
        return self.connected[item]
