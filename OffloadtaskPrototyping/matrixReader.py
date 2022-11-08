import json_numpy
import json
import random
from time import sleep
from datetime import datetime, timedelta

f = open("matrices.json", "r")
encoded_matrices = json.loads(f.read())
f.close()

print(len(encoded_matrices))

while (len(encoded_matrices) != 0):
    pair = random.choice(encoded_matrices)
    pair["mat1"] = json_numpy.loads(pair["mat1"])
    pair["mat2"] = json_numpy.loads(pair["mat2"])
    pair["deadline"] = datetime.now() + timedelta(pair["deadlineSeconds"])
    print(pair)
    sleep(3)