from collections import deque

from machineQueue import MachineQueue

# the task queue is a list of pairs where both elements are matrices
task_queue: deque[dict] = deque()
machines: MachineQueue = MachineQueue()
client_inputs: deque[dict] = deque()
late_tasks: list[tuple[int, float]] = []
results: list[dict] = []
completed_tasks: int = 0
start_machine_timer: float = 0
auctions: dict = {}
