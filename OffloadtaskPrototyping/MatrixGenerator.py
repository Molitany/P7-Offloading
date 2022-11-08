import numpy
import json_numpy
import json
import random

MIN_MAT_SHAPE = 75
MAX_MAT_SHAPE = 125
MIN_DEADLINE  = 10
MAX_DEADLINE  = 50

matrix_array = []
for i in range(0,100):
    shapeNumbers = random.sample(range(MIN_MAT_SHAPE, MAX_MAT_SHAPE), 3)
    mat1 = numpy.random.rand(shapeNumbers[0],shapeNumbers[1])
    mat2 = numpy.random.rand(shapeNumbers[1],shapeNumbers[2])
    deadlineSeconds = random.randint(MIN_DEADLINE,MAX_DEADLINE)
    pair = {
        "mat1" : json_numpy.dumps(mat1),
        "mat2" : json_numpy.dumps(mat2),
        "deadlineSeconds" : deadlineSeconds
    }
    matrix_array.append(pair)

print(len(matrix_array))

f = open("matrices.json", "w")
f.write(json.dumps(matrix_array))
f.close()