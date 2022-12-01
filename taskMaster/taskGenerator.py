from collections import deque
import numpy
import random


def _average(lst):
    return sum(lst) / len(lst)

def generate_tasks(amount=5, min_mat_shape=75, max_mat_shape=125, min_deadline=10, max_deadline=75, fixed_seed=True, offloading_parameters={}) -> deque[dict]:
    '''
    Generates matrix pairs with the given parameters.\n
    The pairs have a deadline_seconds, max_reward and max_shape_number, fine and offloading_parameters.
    '''
    if fixed_seed: random.seed(69)
    
    matrix_array = deque()
    for i in range(0,amount):
        shape_numbers = random.choices(range(min_mat_shape, max_mat_shape+1), k=3)
        mat1 = numpy.random.rand(shape_numbers[0],shape_numbers[1])
        mat2 = numpy.random.rand(shape_numbers[1],shape_numbers[2])
        deadline_seconds = random.randint(min_deadline,max_deadline)
        fine = offloading_parameters.get('fines') if (max_deadline - deadline_seconds) * _average(shape_numbers) * 2 else 0

        a: list = list()
        b: list = list()
        for i in range(len(mat1)):
            a.append(list(mat1[i]))
        for i in range(len(mat2)):
            b.append(list(mat2[i]))
        
        pair = {
            'mat1': a, 
            'mat2': b, 
            'deadline_seconds': deadline_seconds, 
            'max_reward': (max_deadline - deadline_seconds) * _average(shape_numbers), 
            'fine': fine,
            'max_shape_number': max(shape_numbers), 
            'offloading_parameters': offloading_parameters
        }
        matrix_array.append(pair)
    return matrix_array