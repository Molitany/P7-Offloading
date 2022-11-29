import random
from time import sleep
from datetime import datetime, timedelta
from MatrixGenerator import generate_matrices

matrices = generate_matrices()

print(len(matrices))

while (len(matrices) != 0):
    pair = random.choice(matrices)
    pair["deadline"] = datetime.now() + timedelta(pair["deadlineSeconds"])
    print(pair)
    sleep(3)