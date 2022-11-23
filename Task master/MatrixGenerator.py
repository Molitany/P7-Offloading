import numpy
import random

def Average(lst):
    return sum(lst) / len(lst)

def generate_matrices(amount=100, min_mat_shape=75, max_mat_shape=125, min_deadline=10, max_deadline=75, fixed_seed=True):
    if fixed_seed: random.seed(69)
    
    matrix_array = []
    for i in range(0,amount):

        shape_numbers = random.choices(range(min_mat_shape, max_mat_shape+1), k=3)
        mat1 = numpy.random.rand(shape_numbers[0],shape_numbers[1])
        mat2 = numpy.random.rand(shape_numbers[1],shape_numbers[2])
        deadlineSeconds = random.randint(min_deadline,max_deadline)

        a: list = list()
        b: list = list()
        for i in range(len(mat1)):
            a.append(list(mat1[i]))
        for i in range(len(mat2)):
            b.append(list(mat2[i]))
        
        pair = {
            "mat1" : a,
            "mat2" : b,
            "deadlineSeconds" : deadlineSeconds,
            "max_reward" : (max_deadline - deadlineSeconds) * Average(shape_numbers),
            "max_shape_number" : max(shape_numbers)
        }
        matrix_array.append(pair)
    return matrix_array