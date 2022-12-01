import json

class Pair():
    def __init__(self, a: list[list[int]], b: list[list[int]], deadline_seconds: int, max_reward: int, max_shape_number: int, offloading_parameters: dict):
        self.mat1 = a
        self.mat2 = b
        self.deadline_seconds = deadline_seconds
        self.max_reward = max_reward
        self.max_shape_number = max_shape_number
        self.offloading_parameters = offloading_parameters

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
