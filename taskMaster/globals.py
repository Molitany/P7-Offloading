from collections import deque
from Pair import Pair

# the task queue is a list of pairs where both elements are matrices
task_queue: deque[Pair] = deque()
client_inputs: deque[dict] = deque()