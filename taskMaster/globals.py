from collections import deque

# the task queue is a list of pairs where both elements are matrices
task_queue: deque[dict] = deque()
client_inputs: deque[dict] = deque()
late_tasks: list[tuple[int, float]] = []
