import numpy
import json_numpy
import json
import random

def generate_matrices(amount=100, min_mat_shape=75, max_mat_shape=125, min_deadline=10, max_deadline=75):
    random.seed(69)
    matrix_array = []
    for i in range(0,amount):
        shapeNumbers = random.sample(range(min_mat_shape, max_mat_shape), 3)
        mat1 = numpy.random.rand(shapeNumbers[0],shapeNumbers[1])
        mat2 = numpy.random.rand(shapeNumbers[1],shapeNumbers[2])
        deadlineSeconds = random.randint(min_deadline,max_deadline)
        pair = {
            "mat1" : json_numpy.dumps(mat1),
            "mat2" : json_numpy.dumps(mat2),
            "deadlineSeconds" : deadlineSeconds
        }
        matrix_array.append(pair)
    return matrix_array