import json

class Pair():
    def __init__(self, a, b, deadline_seconds, max_reward, max_shape_number):
        self.mat1 = a
        self.mat2 = b
        self.deadline_seconds = deadline_seconds
        self.max_reward = max_reward
        self.max_shape_number = max_shape_number

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
